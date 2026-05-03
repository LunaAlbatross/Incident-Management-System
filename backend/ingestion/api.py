from fastapi import APIRouter, HTTPException, Depends, Request
from ..models.schemas import SignalCreate
import os
import json
import time
import logging
from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = "raw_signals"

# Global structures
producer = None
rate_limits = {}
metrics = {"signals_count": 0}

async def get_kafka_producer():
    global producer
    if producer is None:
        producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
        await producer.start()
    return producer

async def check_rate_limit(request: Request):
    client_ip = request.client.host
    now = time.time()
    
    if client_ip in rate_limits:
        window_start, count = rate_limits[client_ip]
        if now - window_start > 1.0:
            rate_limits[client_ip] = (now, 1)
        else:
            if count >= 1000:
                raise HTTPException(status_code=429, detail="Too Many Requests")
            rate_limits[client_ip] = (window_start, count + 1)
    else:
        rate_limits[client_ip] = (now, 1)
@router.post("/")
async def ingest_signal(signal: SignalCreate, request: Request, prod: AIOKafkaProducer = Depends(get_kafka_producer)):
    await check_rate_limit(request)
    metrics["signals_count"] += 1
    payload_str = signal.json()
    try:
        await prod.send_and_wait(KAFKA_TOPIC, payload_str.encode("utf-8"))
    except Exception as e:
        logger.error(f"Kafka push failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to ingest signal")
    
    return {"status": "accepted"}
