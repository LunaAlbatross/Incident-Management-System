import asyncio
import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .ingestion.api import router as ingestion_router
from .database.connection import engine, get_db, SessionLocal
from .database.models import WorkItemModel, RCAModel, RawSignalModel, Base
from .models.schemas import WorkItemResponse, RCA, WorkItemStateEnum
from .domain.state_pattern import StateContext, StateException
from .ingestion.api import metrics
from .worker.consumer import consume

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Incident Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion_router)

# In-memory dashboard cache
dashboard_cache = []

async def monitor_throughput():
    while True:
        try:
            count = metrics["signals_count"]
            logger.info(f"--- Throughput: {count / 5.0} signals/sec ---")
            
            # Reset counter
            metrics["signals_count"] = 0
            
            # Refresh cache
            db = SessionLocal()
            try:
                items = db.query(WorkItemModel).order_by(WorkItemModel.created_at.desc()).all()
                global dashboard_cache
                dashboard_cache = items
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in monitor: {e}")
        
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_throughput())
    asyncio.create_task(consume())

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/incidents", response_model=list[WorkItemResponse])
def get_incidents(db: Session = Depends(get_db)):
    if dashboard_cache:
        return dashboard_cache
    incidents = db.query(WorkItemModel).order_by(WorkItemModel.created_at.desc()).all()
    return incidents

@app.get("/incidents/{item_id}", response_model=WorkItemResponse)
def get_incident(item_id: int, db: Session = Depends(get_db)):
    incident = db.query(WorkItemModel).filter(WorkItemModel.id == item_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@app.get("/incidents/{item_id}/signals")
def get_incident_signals(item_id: int, db: Session = Depends(get_db)):
    signals = db.query(RawSignalModel).filter(RawSignalModel.work_item_id == item_id).all()
    return signals

@app.get("/metrics/aggregations")
def get_aggregations(db: Session = Depends(get_db)):
    # Simple aggregation: Count signals per severity
    from sqlalchemy import func
    stats = db.query(
        RawSignalModel.severity, 
        func.count(RawSignalModel.id).label("count")
    ).group_by(RawSignalModel.severity).all()
    
    # Also count incidents per state
    state_stats = db.query(
        WorkItemModel.state,
        func.count(WorkItemModel.id).label("count")
    ).group_by(WorkItemModel.state).all()

    return {
        "signals_by_severity": {s: c for s, c in stats},
        "incidents_by_state": {s.value: c for s, c in state_stats}
    }

@app.put("/incidents/{item_id}/state")
def update_incident_state(item_id: int, state: WorkItemStateEnum, db: Session = Depends(get_db)):
    incident = db.query(WorkItemModel).filter(WorkItemModel.id == item_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    ctx = StateContext(incident)
    try:
        ctx.transition_to(state, db)
        db.commit()
        db.refresh(incident)
        return incident
    except StateException as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/incidents/{item_id}/rca")
def submit_rca(item_id: int, rca_data: RCA, db: Session = Depends(get_db)):
    incident = db.query(WorkItemModel).filter(WorkItemModel.id == item_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if incident.rca:
        raise HTTPException(status_code=400, detail="RCA already exists for this incident")
    
    new_rca = RCAModel(
        work_item_id=incident.id,
        root_cause_category=rca_data.root_cause_category,
        fix_applied=rca_data.fix_applied,
        prevention_steps=rca_data.prevention_steps,
        incident_start=rca_data.incident_start,
        incident_end=rca_data.incident_end
    )
    db.add(new_rca)
    db.commit()
    return {"status": "RCA submitted"}
