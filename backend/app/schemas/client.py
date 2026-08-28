from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ClientCreate(BaseModel):
    name: str
    address: str
    zone: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    zone: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class ClientOut(BaseModel):
    id: int
    name: str
    address: str
    zone: Optional[str]
    latitude: float
    longitude: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)