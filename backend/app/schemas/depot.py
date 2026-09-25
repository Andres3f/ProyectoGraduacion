from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class DepotBase(BaseModel):
    name: str
    address: Optional[str] = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class DepotCreate(DepotBase):
    is_default: bool = False


class DepotUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class DepotOut(DepotBase):
    id: int
    is_default: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)