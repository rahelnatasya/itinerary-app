from uuid import UUID

from database import SessionLocal
import models


def process_trip(trip_id: str) -> None:
    db = SessionLocal()
    trip = None
    try:
        trip_uuid = UUID(trip_id)
        trip = db.query(models.Trip).filter(models.Trip.id == trip_uuid).first()
        if not trip:
            return

        ai_insight = {
            "summary": "Rute optimal untuk 1 hari: mulai dari Kawah Putih, lanjut ke Situ Patenggang.",
            "feasible_destinations": ["Kawah Putih", "Situ Patenggang"],
            "removed_destinations": ["Pantai Pelabuhan Ratu"],
            "removal_reason": "Jarak terlalu jauh, estimasi 4.5 jam dari titik sebelumnya.",
            "ordered_route": ["Kawah Putih", "Situ Patenggang"],
        }

        feasible_names = set(ai_insight["feasible_destinations"])
        for dest in trip.destinations:
            dest.is_feasible = dest.name in feasible_names

        trip.ai_insight = ai_insight
        trip.status = "completed"
        db.commit()
    except Exception:
        db.rollback()
        if trip:
            try:
                trip.status = "failed"
                db.commit()
            except Exception:
                db.rollback()
        raise
    finally:
        db.close()
