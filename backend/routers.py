import asyncio
import json
import os
from uuid import UUID

import redis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from rq import Queue
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, get_current_user_from_token
from database import SessionLocal, get_db
import models
from repository import DestinationRepository, TripRepository
from schemas import (
    DestinationCreate,
    DestinationRead,
    DestinationUpdate,
    DestinationVoteRequest,
    GuestAuthRequest,
    TripCreate,
    TripRead,
)
from worker.tasks import process_trip

router = APIRouter(prefix="/api", tags=["api"])

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_conn = redis.from_url(redis_url)
queue = Queue("default", connection=redis_conn)


@router.post("/destinations", response_model=DestinationRead, status_code=status.HTTP_201_CREATED)
def create_destination(
    payload: DestinationCreate,
    db: Session = Depends(get_db),
    user_name: str = Depends(get_current_user),
):
    trip = TripRepository.get_trip_by_id(db, payload.trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    dest = DestinationRepository.create_destination(
        db,
        trip_id=payload.trip_id,
        name=payload.name,
        added_by=user_name,
        notes=payload.notes,
    )
    return dest


@router.post("/trips", status_code=status.HTTP_201_CREATED)
def create_trip(
    payload: TripCreate,
    db: Session = Depends(get_db),
    user_name: str = Depends(get_current_user),
):
    trip = TripRepository.create_trip(
        db,
        title=payload.title,
        trip_date=payload.trip_date,
        start_location=payload.start_location,
    )
    return {"id": str(trip.id)}


@router.put("/destinations/{id}", response_model=DestinationRead)
def update_destination(
    id: UUID,
    payload: DestinationUpdate,
    db: Session = Depends(get_db),
    user_name: str = Depends(get_current_user),
):
    dest = DestinationRepository.update_destination(
        db,
        dest_id=id,
        name=payload.name,
        notes=payload.notes,
        client_version=payload.version,
    )
    return dest


@router.post("/destinations/{destination_id}/vote", response_model=DestinationRead)
def vote_destination(
    destination_id: UUID,
    payload: DestinationVoteRequest,
    db: Session = Depends(get_db),
    user_name: str = Depends(get_current_user),
):
    dest = db.query(models.Destination).filter(models.Destination.id == destination_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")

    vote_type = payload.vote_type
    if vote_type not in {"like", "dislike"}:
        raise HTTPException(status_code=400, detail="Invalid vote_type")

    existing_trip_vote = (
        db.query(models.DestinationVote)
        .join(models.Destination, models.Destination.id == models.DestinationVote.destination_id)
        .filter(
            models.DestinationVote.user_name == user_name,
            models.Destination.trip_id == dest.trip_id,
        )
        .first()
    )

    if existing_trip_vote and existing_trip_vote.destination_id != destination_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Anda hanya memiliki 1 hak suara di itinerary ini! "
                "Batalan vote sebelumnya jika ingin pindah pilihan."
            ),
        )

    existing_vote = existing_trip_vote

    if existing_vote:
        if existing_vote.vote_type == vote_type:
            if vote_type == "like":
                dest.likes = max(dest.likes - 1, 0)
            else:
                dest.dislikes = max(dest.dislikes - 1, 0)
            db.delete(existing_vote)
        else:
            if existing_vote.vote_type == "like":
                dest.likes = max(dest.likes - 1, 0)
            else:
                dest.dislikes = max(dest.dislikes - 1, 0)

            existing_vote.vote_type = vote_type

            if vote_type == "like":
                dest.likes += 1
            else:
                dest.dislikes += 1
    else:
        new_vote = models.DestinationVote(
            destination_id=destination_id,
            user_name=user_name,
            vote_type=vote_type,
        )
        db.add(new_vote)
        if vote_type == "like":
            dest.likes += 1
        else:
            dest.dislikes += 1

    db.commit()
    db.refresh(dest)
    return dest


@router.post("/auth/guest")
def guest_auth(payload: GuestAuthRequest):
    token = create_access_token({"sub": payload.name})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/trips/{id}", response_model=TripRead)
def get_trip(id: UUID, db: Session = Depends(get_db), user_name: str = Depends(get_current_user)):
    trip = TripRepository.get_trip_by_id(db, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.get("/trips/join/{room_code}")
def join_trip(
    room_code: str,
    db: Session = Depends(get_db),
    user_name: str = Depends(get_current_user),
):
    trip = TripRepository.get_trip_by_room_code(db, room_code)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"id": str(trip.id)}


@router.post("/trips/{id}/analyze")
def analyze_trip(
    id: UUID,
    db: Session = Depends(get_db),
    user_name: str = Depends(get_current_user),
):
    trip = TripRepository.get_trip_by_id(db, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.status == "processing":
        raise HTTPException(status_code=409, detail="Trip is already being processed.")

    trip.status = "processing"
    db.commit()
    db.refresh(trip)

    queue.enqueue(process_trip, str(trip.id))

    return {"trip_id": str(trip.id), "status": "processing"}


@router.get("/trips/{id}/stream")
async def stream_trip(id: UUID, token: str = Query(...)):
    get_current_user_from_token(token)
    async def event_generator():
        while True:
            db = SessionLocal()
            try:
                trip = TripRepository.get_trip_by_id(db, id)
                if not trip:
                    payload = {"error": "Trip not found"}
                else:
                    payload = {
                        "id": str(trip.id),
                        "status": trip.status,
                        "destinations_count": len(trip.destinations),
                        "version": trip.version,
                    }
                yield f"data: {json.dumps(payload)}\n\n"
            except Exception as exc:
                error_payload = {"error": f"Stream error: {exc}"}
                yield f"data: {json.dumps(error_payload)}\n\n"
            finally:
                db.close()

            await asyncio.sleep(1)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )
