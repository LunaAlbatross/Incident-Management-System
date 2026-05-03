import asyncio
import os
import json
import logging
import time
from aiokafka import AIOKafkaConsumer
from ..database.connection import SessionLocal
from ..database.models import WorkItemModel, RawSignalModel
from ..models.schemas import WorkItemStateEnum
from ..domain.strategy_pattern import get_alert_strategy, AlertContext

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = "raw_signals"

debounce_locks = {}

async def process_signal(signal_data: dict):
    component_id = signal_data.get("component_id")
    severity = signal_data.get("severity", "P3")
    
    db = SessionLocal()
    try:
        # Data Lake sink
        raw_signal = RawSignalModel(
            component_id=component_id,
            severity=severity,
            payload=signal_data.get("payload", {})
        )
        db.add(raw_signal)
        
        now = time.time()
        is_new = False
        if component_id not in debounce_locks or (now - debounce_locks[component_id] > 10.0):
            debounce_locks[component_id] = now
            is_new = True
            
        existing = db.query(WorkItemModel).filter(
            WorkItemModel.component_id == component_id,
            WorkItemModel.state.in_([WorkItemStateEnum.OPEN, WorkItemStateEnum.INVESTIGATING, WorkItemStateEnum.RESOLVED])
        ).first()
        
        if is_new and not existing:
            new_item = WorkItemModel(component_id=component_id, severity=severity, state=WorkItemStateEnum.OPEN)
            db.add(new_item)
            db.commit()
            db.refresh(new_item)
            logger.info(f"Created new Work Item {new_item.id} for {component_id}")
            
            # Link the signal we just created
            raw_signal.work_item_id = new_item.id
            
            strategy = get_alert_strategy(severity)
            context = AlertContext(strategy)
            context.execute_alert(component_id, signal_data)
        elif existing:
            raw_signal.work_item_id = existing.id
            db.commit()
        else:
            db.commit()
    except Exception as e:
        logger.error(f"Error processing signal: {e}")
        db.rollback()
    finally:
        db.close()



async def consume():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="ims_worker_group",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest"
    )
    
    while True:
        try:
            await consumer.start()
            logger.info("Kafka Consumer started.")
            break
        except Exception as e:
            logger.error(f"Failed to connect to Kafka, retrying in 5s... ({e})")
            await asyncio.sleep(5)
            
    try:
        async for msg in consumer:
            await process_signal(msg.value)
    except Exception as e:
        logger.error(f"Consumer error: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume())
