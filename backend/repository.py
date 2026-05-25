import secrets
import string
import uuid
from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models

class TripRepository:
    @staticmethod
    def get_trip_by_id(db: Session, trip_id: uuid.UUID):
        return db.query(models.Trip).filter(models.Trip.id == trip_id).first()

    @staticmethod
    def get_trip_by_room_code(db: Session, room_code: str):
        return db.query(models.Trip).filter(models.Trip.room_code == room_code).first()

    @staticmethod
    def create_trip(
        db: Session,
        title: str,
        trip_date: Optional[date] = None,
        start_location: Optional[str] = None,
    ):
        room_code = TripRepository._generate_room_code(db)
        db_trip = models.Trip(
            title=title,
            room_code=room_code,
            trip_date=trip_date,
            start_location=start_location,
        )
        db.add(db_trip)
        db.commit()
        db.refresh(db_trip)
        return db_trip

    @staticmethod
    def _generate_room_code(db: Session, length: int = 6) -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(10):
            code = "".join(secrets.choice(alphabet) for _ in range(length))
            exists = db.query(models.Trip).filter(models.Trip.room_code == code).first()
            if not exists:
                return code
        raise HTTPException(status_code=500, detail="Failed to generate unique room code")

class DestinationRepository:
    @staticmethod
    def create_destination(db: Session, trip_id: uuid.UUID, name: str, added_by: str, notes: str = None):
        db_dest = models.Destination(trip_id=trip_id, name=name, added_by=added_by, notes=notes)
        db.add(db_dest)
        db.commit()
        db.refresh(db_dest)
        return db_dest

    @staticmethod
    def update_destination(db: Session, dest_id: uuid.UUID, name: str, notes: str, client_version: int):
        dest = db.query(models.Destination).filter(models.Destination.id == dest_id).first()
        if not dest:
            raise HTTPException(status_code=404, detail="Destination not found")
        
        # Deteksi manual Race Condition (Optimistic Locking) sebelum melakukan commit
        if dest.version != client_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict: destination was updated by another user. Please refresh."
            )
        
        dest.name = name
        dest.notes = notes
        
        try:
            db.commit()
            db.refresh(dest)
            return dest
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict: A concurrency error occurred. Please refresh."
            )