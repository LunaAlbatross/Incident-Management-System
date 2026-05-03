from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class AlertStrategy(ABC):
    @abstractmethod
    def send_alert(self, component_id: str, payload: dict):
        pass

class P0AlertStrategy(AlertStrategy):
    def send_alert(self, component_id: str, payload: dict):
        logger.error(f"[P0 ALERT - CRITICAL] {component_id} is down! Immediate action required. Payload: {payload}")
        # In a real system, this would call PagerDuty, Twilio, etc.

class P1AlertStrategy(AlertStrategy):
    def send_alert(self, component_id: str, payload: dict):
        logger.warning(f"[P1 ALERT - HIGH] {component_id} is experiencing issues. Payload: {payload}")

class P2AlertStrategy(AlertStrategy):
    def send_alert(self, component_id: str, payload: dict):
        logger.info(f"[P2 ALERT - MEDIUM] {component_id} degraded. Payload: {payload}")

class P3AlertStrategy(AlertStrategy):
    def send_alert(self, component_id: str, payload: dict):
        logger.debug(f"[P3 ALERT - LOW] {component_id} minor issue. Payload: {payload}")

class AlertContext:
    def __init__(self, strategy: AlertStrategy):
        self.strategy = strategy
    
    def execute_alert(self, component_id: str, payload: dict):
        self.strategy.send_alert(component_id, payload)

def get_alert_strategy(severity: str) -> AlertStrategy:
    if severity == "P0":
        return P0AlertStrategy()
    elif severity == "P1":
        return P1AlertStrategy()
    elif severity == "P2":
        return P2AlertStrategy()
    else:
        return P3AlertStrategy()
