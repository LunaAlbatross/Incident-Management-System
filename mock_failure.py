import asyncio
import httpx
import time
import random
from collections import Counter

API_URL = "http://localhost:8000/ingest/"
CONCURRENCY_LIMIT = 500  # Prevent exhausting local sockets
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

async def send_signal(client, component_id, severity, error_msg):
    payload = {
        "component_id": component_id,
        "severity": severity,
        "payload": {
            "error": error_msg,
            "region": "us-east-1",
            "cpu_usage": random.randint(80, 100)
        }
    }
    async with semaphore:
        try:
            # Using a short timeout since we are hammering localhost
            response = await client.post(API_URL, json=payload, timeout=10.0)
            return response.status_code
        except Exception as e:
            return 500


async def simulate_outage():
    print("🚀 Initializing MASSIVE Signal Storm Simulation (10,000 hits)...")
    print("   Expect to see many 429 (Too Many Requests) due to your Rate Limiter!\n")
    
    limits = httpx.Limits(max_keepalive_connections=500, max_connections=500)
    async with httpx.AsyncClient(limits=limits) as client:
        # Phase 1: The Root Cause (Database Crash)
        print("🔴 Phase 1: Primary Database (RDBMS_PROD_01) is failing... (Sending 2,000 signals)")
        db_tasks = [send_signal(client, "RDBMS_PROD_01", "P0", {"error": "Connection Timeout", "pool_usage": "100%"}) for _ in range(2000)]
        results1 = await asyncio.gather(*db_tasks)
        print(f"   HTTP Statuses received: {dict(Counter(results1))}\n")
        
        await asyncio.sleep(1) # Delay before the cascade starts
        
        # Phase 2: Downstream Service Failures
        print("🟠 Phase 2: Downstream services (AUTH & PAYMENTS) are struggling... (Sending 3,000 signals)")
        service_tasks = []
        for _ in range(1500):
            service_tasks.append(send_signal(client, "AUTH_SERVICE", "P1", {"msg": "Upstream DB Unreachable"}))
            service_tasks.append(send_signal(client, "PAYMENT_GATEWAY", "P0", {"msg": "Transaction Failed"}))
        results2 = await asyncio.gather(*service_tasks)
        print(f"   HTTP Statuses received: {dict(Counter(results2))}\n")
        
        await asyncio.sleep(1)
        
        # Phase 3: Background Noise & Non-Critical issues
        print("🟡 Phase 3: Non-critical noise (Cache & Search)... (Sending 5,000 signals)")
        noise_tasks = []
        for _ in range(2500):
            noise_tasks.append(send_signal(client, "REDIS_CACHE_02", "P2", {"msg": "High CPU", "utilization": "92%"}))
            noise_tasks.append(send_signal(client, "ELASTIC_SEARCH_CLUSTER", "P3", {"msg": "Slow indexing"}))
        
        results3 = await asyncio.gather(*noise_tasks)
        print(f"   HTTP Statuses received: {dict(Counter(results3))}\n")
        
        print("✅ Simulation completed.")
        print("Check your dashboard at http://localhost:5173 to see the timeline!")

if __name__ == "__main__":
    asyncio.run(simulate_outage())
