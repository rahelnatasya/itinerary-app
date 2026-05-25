import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Date, DateTime, Text, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from database import Base

class Trip(Base):
    __tablename__ = "trips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    trip_date = Column(Date, nullable=True)
    start_location = Column(String, nullable=True)
    room_code = Column(String(10), unique=True, index=True)
    status = Column(String, default="draft")  # draft, processing, completed, failed
    ai_insight = Column(JSONB, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relasi ke tabel Destination (One-to-Many)
    destinations = relationship("Destination", back_populates="trip", cascade="all, delete-orphan")

    # Konfigurasi Otomatis Optimistic Locking untuk SQLAlchemy
    __mapper_args__ = {
        "version_id_col": version
    }

class Destination(Base):
    __tablename__ = "destinations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    added_by = Column(String, nullable=False)  # Nama statis untuk Fase 1
    notes = Column(Text, nullable=True)
    order_index = Column(Integer, default=0)
    is_feasible = Column(Boolean, nullable=True)
    version = Column(Integer, default=1, nullable=False)

    # Relasi balik ke Trip
    trip = relationship("Trip", back_populates="destinations")

    # Konfigurasi Otomatis Optimistic Locking untuk SQLAlchemy
    __mapper_args__ = {
        "version_id_col": version
    }