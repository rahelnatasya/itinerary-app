import os
from uuid import UUID

import redis
from fastapi import APIRouter, Depends, HTTPException, status
from rq import Queue
from sqlalchemy.orm import Session

from database import get_db
from repository import DestinationRepository, TripRepository
from schemas import DestinationCreate, DestinationRead, DestinationUpdate, TripCreate, TripRead
from worker.tasks import process_trip

router = APIRouter(prefix="/api", tags=["api"])

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_conn = redis.from_url(redis_url)
queue = Queue("default", connection=redis_conn)


@router.post("/destinations", response_model=DestinationRead, status_code=status.HTTP_201_CREATED)
def create_destination(payload: DestinationCreate, db: Session = Depends(get_db)):
    trip = TripRepository.get_trip_by_id(db, payload.trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    dest = DestinationRepository.create_destination(
        db,
        trip_id=payload.trip_id,
        name=payload.name,
        added_by=payload.added_by,
        notes=payload.notes,
    )
    return dest


@router.post("/trips", status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, db: Session = Depends(get_db)):
    trip = TripRepository.create_trip(
        db,
        title=payload.title,
        trip_date=payload.trip_date,
        start_location=payload.start_location,
    )
    return {"id": str(trip.id)}


@router.put("/destinations/{id}", response_model=DestinationRead)
def update_destination(id: UUID, payload: DestinationUpdate, db: Session = Depends(get_db)):
    dest = DestinationRepository.update_destination(
        db,
        dest_id=id,
        name=payload.name,
        notes=payload.notes,
        client_version=payload.version,
    )
    return dest


@router.get("/trips/{id}", response_model=TripRead)
def get_trip(id: UUID, db: Session = Depends(get_db)):
    trip = TripRepository.get_trip_by_id(db, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.get("/trips/join/{room_code}")
def join_trip(room_code: str, db: Session = Depends(get_db)):
    trip = TripRepository.get_trip_by_room_code(db, room_code)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"id": str(trip.id)}


@router.post("/trips/{id}/analyze")
def analyze_trip(id: UUID, db: Session = Depends(get_db)):
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
