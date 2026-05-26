from datetime import date
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DestinationCreate(BaseModel):
    trip_id: UUID
    name: str
    added_by: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DestinationUpdate(BaseModel):
    name: str
    notes: Optional[str] = None
    version: int

    model_config = ConfigDict(from_attributes=True)


class DestinationRead(BaseModel):
    id: UUID
    name: str
    added_by: str
    notes: Optional[str] = None
    order_index: int
    is_feasible: Optional[bool] = None
    likes: int
    dislikes: int
    version: int

    model_config = ConfigDict(from_attributes=True)


class TripCreate(BaseModel):
    title: str
    trip_date: Optional[date] = None
    start_location: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TripRead(BaseModel):
    id: UUID
    title: str
    trip_date: Optional[date] = None
    start_location: Optional[str] = None
    room_code: Optional[str] = None
    status: str
    version: int
    ai_insight: Optional[Any] = None
    destinations: List[DestinationRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DestinationVoteRequest(BaseModel):
    vote_type: str

    model_config = ConfigDict(from_attributes=True)


class GuestAuthRequest(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)
