from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text, JSON
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from ..models.schemas import WorkItemStateEnum

Base = declarative_base()

class WorkItemModel(Base):
    __tablename__ = "work_items"

    id = Column(Integer, primary_key=True, index=True)
    component_id = Column(String, index=True)
    severity = Column(String, default="P3")
    state = Column(Enum(WorkItemStateEnum), default=WorkItemStateEnum.OPEN)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    mttr_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rca = relationship("RCAModel", back_populates="work_item", uselist=False)

class RCAModel(Base):
    __tablename__ = "rca_records"

    id = Column(Integer, primary_key=True, index=True)
    work_item_id = Column(Integer, ForeignKey("work_items.id"), unique=True)
    root_cause_category = Column(String)
    fix_applied = Column(Text)
    prevention_steps = Column(Text)
    incident_start = Column(DateTime)
    incident_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    work_item = relationship("WorkItemModel", back_populates="rca")

class RawSignalModel(Base):
    __tablename__ = "raw_signals"

    id = Column(Integer, primary_key=True, index=True)
    work_item_id = Column(Integer, ForeignKey("work_items.id"), nullable=True)
    component_id = Column(String, index=True)
    severity = Column(String)
    payload = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
