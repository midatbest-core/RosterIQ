import sys
import os
import time
import asyncio
import psutil
import json
import statistics
from typing import Any
import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

sys.path.insert(0, os.path.abspath("backend"))

# Force test configuration
BENCH_DB_PATH = os.path.abspath("scratch/benchmarks/bench_isolated.db")
BENCH_DB_URL = f"sqlite+pysqlite:///{BENCH_DB_PATH.replace(os.sep, '/')}"

os.environ["ROSTERIQ_DATABASE_URL"] = BENCH_DB_URL
os.environ["ROSTERIQ_ENVIRONMENT"] = "development"
os.environ["ROSTERIQ_JWT_SECRET"] = "benchmark-secret-key-at-least-32-chars-long"

from app.core.config import get_settings
get_settings.cache_clear()

# Override DB session engine with high capacity pool for concurrency test
import app.db.session as db_session
db_session.engine.dispose()
connect_args = {"check_same_thread": False, "timeout": 60}
tuned_engine = create_engine(
    BENCH_DB_URL,
    poolclass=QueuePool,
    pool_size=100,
    max_overflow=50,
    pool_timeout=30.0,
    pool_pre_ping=True,
    connect_args=connect_args
)
db_session.engine = tuned_engine
db_session.SessionLocal = sessionmaker(bind=tuned_engine, autoflush=False, expire_on_commit=False)

from app.modules.roster.models import Roster
with db_session.SessionLocal() as session:
    roster = session.scalars(select(Roster)).first()
    ROSTER_ID = str(roster.id) if roster else ""

print(f"Loaded benchmark roster: {ROSTER_ID}")

from app.main import app

USERS = [
    {"email": "admin@bench.io", "password": "BenchSecret123!", "role": "ADMIN"},
    {"email": "ops@bench.io", "password": "BenchSecret123!", "role": "OPERATIONS_MANAGER"},
    {"email": "lead@bench.io", "password": "BenchSecret123!", "role": "POD_LEAD"},
    {"email": "brand@bench.io", "password": "BenchSecret123!", "role": "BRAND_USER"},
    {"email": "emp@bench.io", "password": "BenchSecret123!", "role": "EMPLOYEE"},
]

async def authenticate_user(client: httpx.AsyncClient, user_spec: dict) -> dict:
    t0 = time.perf_counter()
    r = await client.post("/api/v1/auth/login", json={"email": user_spec["email"], "password": user_spec["password"]})
    lat = (time.perf_counter() - t0) * 1000.0
    return {"status": r.status_code, "latency_ms": lat, "cookies": client.cookies}

async def execute_authenticated_cycle(client: httpx.AsyncClient, role: str) -> list[dict]:
    results = []
    
    # 1. User details (/auth/me)
    t0 = time.perf_counter()
    r = await client.get("/api/v1/auth/me")
    results.append({"endpoint": "/auth/me", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

    # 2. Notifications (/auth/notifications)
    t0 = time.perf_counter()
    r = await client.get("/api/v1/auth/notifications")
    results.append({"endpoint": "/auth/notifications", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

    # 3. Role specific routes
    if role in ("ADMIN", "OPERATIONS_MANAGER"):
        # Grid
        t0 = time.perf_counter()
        r = await client.get(f"/api/v1/rosters/{ROSTER_ID}/grid?view_type=company")
        results.append({"endpoint": "/rosters/grid", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

        # Analytics
        t0 = time.perf_counter()
        r = await client.get(f"/api/v1/rosters/{ROSTER_ID}/analytics")
        results.append({"endpoint": "/rosters/analytics", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

        # CSV Export
        t0 = time.perf_counter()
        r = await client.get(f"/api/v1/rosters/{ROSTER_ID}/export/csv?view_type=company")
        results.append({"endpoint": "/rosters/export/csv", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

    elif role == "POD_LEAD":
        t0 = time.perf_counter()
        r = await client.get(f"/api/v1/rosters/{ROSTER_ID}/grid?view_type=pod")
        results.append({"endpoint": "/rosters/grid", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

        t0 = time.perf_counter()
        r = await client.get(f"/api/v1/rosters/{ROSTER_ID}/export/csv?view_type=pod")
        results.append({"endpoint": "/rosters/export/csv", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

    elif role == "BRAND_USER":
        t0 = time.perf_counter()
        r = await client.get("/api/v1/brand-portal/me")
        results.append({"endpoint": "/brand-portal/me", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

        t0 = time.perf_counter()
        r = await client.get("/api/v1/brand-portal/requests")
        results.append({"endpoint": "/brand-portal/requests", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

        t0 = time.perf_counter()
        r = await client.get("/api/v1/brand-portal/export/csv")
        results.append({"endpoint": "/brand-portal/export/csv", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

    elif role == "EMPLOYEE":
        t0 = time.perf_counter()
        r = await client.get("/api/v1/employee-portal/me")
        results.append({"endpoint": "/employee-portal/me", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

        t0 = time.perf_counter()
        r = await client.get("/api/v1/employee-portal/tasks")
        results.append({"endpoint": "/employee-portal/tasks", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

        t0 = time.perf_counter()
        r = await client.get("/api/v1/employee-portal/export/csv")
        results.append({"endpoint": "/employee-portal/export/csv", "status": r.status_code, "latency_ms": (time.perf_counter() - t0) * 1000.0, "ok": r.status_code == 200})

    return results

async def worker_session(transport: httpx.ASGITransport, user_spec: dict, stop_time: float, collector: list):
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        auth_res = await authenticate_user(client, user_spec)
        collector.append({"endpoint": "/auth/login", "status": auth_res["status"], "latency_ms": auth_res["latency_ms"], "ok": auth_res["status"] == 200})
        if auth_res["status"] != 200:
            return

        while time.perf_counter() < stop_time:
            batch = await execute_authenticated_cycle(client, user_spec["role"])
            collector.extend(batch)
            await asyncio.sleep(0.02)

async def run_load_test(concurrency: int, duration_sec: int = 5) -> dict:
    transport = httpx.ASGITransport(app=app)
    stop_time = time.perf_counter() + duration_sec
    all_results = []
    
    proc = psutil.Process()
    mem_before = proc.memory_info().rss / (1024**2)
    
    t0 = time.perf_counter()
    tasks = []
    for i in range(concurrency):
        u = USERS[i % len(USERS)]
        tasks.append(worker_session(transport, u, stop_time, all_results))
    
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - t0

    mem_after = proc.memory_info().rss / (1024**2)

    total_requests = len(all_results)
    successful_requests = sum(1 for r in all_results if r["ok"])
    failed_requests = total_requests - successful_requests
    latencies = [r["latency_ms"] for r in all_results] if all_results else [0.0]

    latencies.sort()
    n = len(latencies)
    avg_lat = statistics.mean(latencies) if n else 0.0
    med_lat = statistics.median(latencies) if n else 0.0
    p95_lat = latencies[int(n * 0.95)] if n else 0.0
    p99_lat = latencies[int(n * 0.99)] if n else 0.0
    min_lat = min(latencies) if n else 0.0
    max_lat = max(latencies) if n else 0.0
    rps = total_requests / total_time if total_time > 0 else 0.0

    endpoints = {}
    for ep in ["/auth/login", "/auth/me", "/auth/notifications", "/rosters/grid", "/rosters/analytics", "/rosters/export/csv", "/brand-portal/me", "/brand-portal/requests", "/employee-portal/me", "/employee-portal/tasks"]:
        ep_lats = [r["latency_ms"] for r in all_results if r.get("endpoint") == ep]
        if ep_lats:
            ep_lats.sort()
            ep_n = len(ep_lats)
            endpoints[ep] = {
                "count": ep_n,
                "avg_ms": round(statistics.mean(ep_lats), 2),
                "p95_ms": round(ep_lats[int(ep_n * 0.95)], 2),
                "p99_ms": round(ep_lats[int(ep_n * 0.99)], 2),
            }

    return {
        "concurrency": concurrency,
        "duration_sec": round(total_time, 2),
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "error_rate_pct": round((failed_requests / total_requests) * 100, 2) if total_requests > 0 else 0.0,
        "rps": round(rps, 2),
        "avg_latency_ms": round(avg_lat, 2),
        "median_latency_ms": round(med_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
        "p99_latency_ms": round(p99_lat, 2),
        "min_latency_ms": round(min_lat, 2),
        "max_latency_ms": round(max_lat, 2),
        "mem_delta_mb": round(mem_after - mem_before, 2),
        "peak_mem_mb": round(mem_after, 2),
        "endpoints": endpoints
    }

async def main():
    print("=== Running Authenticated Concurrency API Benchmark (All Tables Registered) ===")
    concurrency_levels = [1, 10, 25, 50, 100]
    suite_results = []
    
    for c in concurrency_levels:
        print(f"Testing {c:3d} concurrent users (duration: 5s)...")
        res = await run_load_test(concurrency=c, duration_sec=5)
        suite_results.append(res)
        print(f"  -> {c:3d} Users: {res['rps']} RPS | Avg: {res['avg_latency_ms']}ms | Med: {res['median_latency_ms']}ms | p95: {res['p95_latency_ms']}ms | p99: {res['p99_latency_ms']}ms | Errors: {res['failed_requests']} ({res['error_rate_pct']}%)")

    with open("scratch/benchmarks/concurrency_benchmark_results.json", "w") as f:
        json.dump(suite_results, f, indent=2)
    print("\nSaved results to scratch/benchmarks/concurrency_benchmark_results.json")

if __name__ == "__main__":
    asyncio.run(main())
