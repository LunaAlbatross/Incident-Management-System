from abc import ABC, abstractmethod
from ..models.schemas import WorkItemStateEnum
from ..database.models import WorkItemModel
from sqlalchemy.orm import Session
from datetime import datetime

class StateException(Exception):
    pass

class WorkItemState(ABC):
    @abstractmethod
    def transition_to(self, new_state: WorkItemStateEnum, work_item: WorkItemModel, db: Session):
        pass

class OpenState(WorkItemState):
    def transition_to(self, new_state: WorkItemStateEnum, work_item: WorkItemModel, db: Session):
        if new_state == WorkItemStateEnum.INVESTIGATING:
            work_item.state = new_state
        elif new_state == WorkItemStateEnum.RESOLVED:
            work_item.state = new_state
        elif new_state == WorkItemStateEnum.CLOSED:
            raise StateException("Cannot close an OPEN incident directly.")
        else:
            raise StateException(f"Invalid transition from OPEN to {new_state.value}")

class InvestigatingState(WorkItemState):
    def transition_to(self, new_state: WorkItemStateEnum, work_item: WorkItemModel, db: Session):
        if new_state == WorkItemStateEnum.RESOLVED:
            work_item.state = new_state
        elif new_state == WorkItemStateEnum.OPEN:
            work_item.state = new_state
        elif new_state == WorkItemStateEnum.CLOSED:
            raise StateException("Cannot close an INVESTIGATING incident directly.")
        else:
            raise StateException(f"Invalid transition from INVESTIGATING to {new_state.value}")

class ResolvedState(WorkItemState):
    def transition_to(self, new_state: WorkItemStateEnum, work_item: WorkItemModel, db: Session):
        if new_state == WorkItemStateEnum.CLOSED:
            # Mandatory RCA check
            if not work_item.rca:
                raise StateException("Cannot transition to CLOSED without an RCA record.")
            
            work_item.state = new_state
            
            # MTTR Calculation based on RCA times
            if work_item.rca.incident_start and work_item.rca.incident_end:
                delta = work_item.rca.incident_end - work_item.rca.incident_start
                work_item.mttr_seconds = delta.total_seconds()
                work_item.start_time = work_item.rca.incident_start
                work_item.end_time = work_item.rca.incident_end
        elif new_state == WorkItemStateEnum.INVESTIGATING:
            work_item.state = new_state
        else:
            raise StateException(f"Invalid transition from RESOLVED to {new_state.value}")

class ClosedState(WorkItemState):
    def transition_to(self, new_state: WorkItemStateEnum, work_item: WorkItemModel, db: Session):
        raise StateException("Incident is already CLOSED. No further transitions allowed.")

def get_state_instance(state_enum: WorkItemStateEnum) -> WorkItemState:
    if state_enum == WorkItemStateEnum.OPEN:
        return OpenState()
    elif state_enum == WorkItemStateEnum.INVESTIGATING:
        return InvestigatingState()
    elif state_enum == WorkItemStateEnum.RESOLVED:
        return ResolvedState()
    elif state_enum == WorkItemStateEnum.CLOSED:
        return ClosedState()
    raise StateException("Unknown state")

class StateContext:
    def __init__(self, work_item: WorkItemModel):
        self.work_item = work_item
        self.state = get_state_instance(work_item.state)
    
    def transition_to(self, new_state: WorkItemStateEnum, db: Session):
        self.state.transition_to(new_state, self.work_item, db)
        self.state = get_state_instance(self.work_item.state)
