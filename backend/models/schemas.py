from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SignalSeverity(str, Enum):
    P0 = "P0" # Critical e.g. RDBMS
    P1 = "P1" # High
    P2 = "P2" # Medium e.g. Cache
    P3 = "P3" # Low

class SignalCreate(BaseModel):
    component_id: str
    severity: SignalSeverity
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class WorkItemStateEnum(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class WorkItemResponse(BaseModel):
    id: int
    component_id: str
    severity: str
    state: WorkItemStateEnum
    start_time: datetime
    end_time: Optional[datetime] = None
    mttr_seconds: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RCA(BaseModel):
    root_cause_category: str
    fix_applied: str
    prevention_steps: str
    incident_start: datetime
    incident_end: datetime
