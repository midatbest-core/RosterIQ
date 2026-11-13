import sys
import os
import time
import asyncio
import psutil
import json
import statistics
from typing import Any
import httpx

sys.path.insert(0, os.path.abspath("backend"))

# Force test configuration
BENCH_DB_PATH = os.path.abspath("scratch/benchmarks/bench_isolated.db")
BENCH_DB_URL = f"sqlite+pysqlite:///{BENCH_DB_PATH.replace(os.sep, '/')}"

os.environ["ROSTERIQ_DATABASE_URL"] = BENCH_DB_URL
os.environ["ROSTERIQ_ENVIRONMENT"] = "development"
os.environ["ROSTERIQ_JWT_SECRET"] = "benchmark-secret-key-at-least-32-chars-long"

from app.core.config import get_settings
get_settings.cache_clear()

from app.main import app

ROSTER_ID = "df5b3575-75df-49aa-a789-0fecf7016291"

USERS = [
    {"email": "admin@bench.io", "password": "BenchSecret123!", "role": "ADMIN"},
    {"email": "ops@bench.io", "password": "BenchSecret123!", "role": "OPERATIONS_MANAGER"},
    {"email": "lead@bench.io", "password": "BenchSecret123!", "role": "POD_LEAD"},
    {"email": "brand@bench.io", "password": "BenchSecret123!", "role": "BRAND_USER"},
    {"email": "emp@bench.io", "password": "BenchSecret123!", "role": "EMPLOYEE"},
]

async def execute_user_journey(client: httpx.AsyncClient, user_spec: dict) -> list[dict]:
    results = []
    
    # 1. Login
    t0 = time.perf_counter()
    r_login = await client.post("/api/v1/auth/login", json={"email": user_spec["email"], "password": user_spec["password"]})
    lat_login = (time.perf_counter() - t0) * 1000.0
    results.append({"endpoint": "/auth/login", "status": r_login.status_code, "latency_ms": lat_login, "ok": r_login.status_code == 200})

    if r_login.status_code != 200:
        return results

    # Extract cookies for authenticated session
    cookies = client.cookies

    # 2. Get Current User (/auth/me)
    t0 = time.perf_counter()
    r_me = await client.get("/api/v1/auth/me", cookies=cookies)
    lat_me = (time.perf_counter() - t0) * 1000.0
    results.append({"endpoint": "/auth/me", "status": r_me.status_code, "latency_ms": lat_me, "ok": r_me.status_code == 200})

    # 3. Role-specific journey
    role = user_spec["role"]
    if role in ("ADMIN", "OPERATIONS_MANAGER"):
        # Grid View
        t0 = time.perf_counter()
        r_grid = await client.get(f"/api/v1/rosters/{ROSTER_ID}/grid?view_type=company", cookies=cookies)
        lat_grid = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/rosters/grid", "status": r_grid.status_code, "latency_ms": lat_grid, "ok": r_grid.status_code == 200})

        # Notifications
        t0 = time.perf_counter()
        r_notif = await client.get("/api/v1/auth/notifications", cookies=cookies)
        lat_notif = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/auth/notifications", "status": r_notif.status_code, "latency_ms": lat_notif, "ok": r_notif.status_code == 200})

        # Analytics
        t0 = time.perf_counter()
        r_ana = await client.get("/api/v1/operations/analytics/overview", cookies=cookies)
        lat_ana = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/analytics/overview", "status": r_ana.status_code, "latency_ms": lat_ana, "ok": r_ana.status_code == 200})

        # CSV Export
        t0 = time.perf_counter()
        r_csv = await client.get(f"/api/v1/rosters/{ROSTER_ID}/export/csv?view_type=company", cookies=cookies)
        lat_csv = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/rosters/export/csv", "status": r_csv.status_code, "latency_ms": lat_csv, "ok": r_csv.status_code == 200})

    elif role == "POD_LEAD":
        # Grid View
        t0 = time.perf_counter()
        r_grid = await client.get(f"/api/v1/rosters/{ROSTER_ID}/grid?view_type=pod", cookies=cookies)
        lat_grid = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/rosters/grid", "status": r_grid.status_code, "latency_ms": lat_grid, "ok": r_grid.status_code == 200})

        # Notifications
        t0 = time.perf_counter()
        r_notif = await client.get("/api/v1/auth/notifications", cookies=cookies)
        lat_notif = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/auth/notifications", "status": r_notif.status_code, "latency_ms": lat_notif, "ok": r_notif.status_code == 200})

        # CSV Export
        t0 = time.perf_counter()
        r_csv = await client.get(f"/api/v1/rosters/{ROSTER_ID}/export/csv?view_type=pod", cookies=cookies)
        lat_csv = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/rosters/export/csv", "status": r_csv.status_code, "latency_ms": lat_csv, "ok": r_csv.status_code == 200})

    elif role == "BRAND_USER":
        # Brand Portal Schedule
        t0 = time.perf_counter()
        r_brand = await client.get("/api/v1/brand-portal/my-schedule", cookies=cookies)
        lat_brand = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/brand-portal/my-schedule", "status": r_brand.status_code, "latency_ms": lat_brand, "ok": r_brand.status_code == 200})

        # Notifications
        t0 = time.perf_counter()
        r_notif = await client.get("/api/v1/auth/notifications", cookies=cookies)
        lat_notif = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/auth/notifications", "status": r_notif.status_code, "latency_ms": lat_notif, "ok": r_notif.status_code == 200})

        # Brand CSV Export
        t0 = time.perf_counter()
        r_csv = await client.get("/api/v1/brand-portal/export/csv", cookies=cookies)
        lat_csv = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/brand-portal/export/csv", "status": r_csv.status_code, "latency_ms": lat_csv, "ok": r_csv.status_code == 200})

    elif role == "EMPLOYEE":
        # Employee Portal Schedule
        t0 = time.perf_counter()
        r_emp = await client.get("/api/v1/employee-portal/my-schedule", cookies=cookies)
        lat_emp = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/employee-portal/my-schedule", "status": r_emp.status_code, "latency_ms": lat_emp, "ok": r_emp.status_code == 200})

        # Notifications
        t0 = time.perf_counter()
        r_notif = await client.get("/api/v1/auth/notifications", cookies=cookies)
        lat_notif = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/auth/notifications", "status": r_notif.status_code, "latency_ms": lat_notif, "ok": r_notif.status_code == 200})

        # Employee CSV Export
        t0 = time.perf_counter()
        r_csv = await client.get("/api/v1/employee-portal/export/csv", cookies=cookies)
        lat_csv = (time.perf_counter() - t0) * 1000.0
        results.append({"endpoint": "/employee-portal/export/csv", "status": r_csv.status_code, "latency_ms": lat_csv, "ok": r_csv.status_code == 200})

    return results

async def worker_loop(client: httpx.AsyncClient, user_spec: dict, stop_time: float, collector: list):
    while time.perf_counter() < stop_time:
        res = await execute_user_journey(client, user_spec)
        collector.extend(res)
        await asyncio.sleep(0.01) # cooperative yield

async def run_load_test(concurrency: int, duration_sec: int = 10) -> dict:
    transport = httpx.ASGITransport(app=app)
    stop_time = time.perf_counter() + duration_sec
    all_results = []
    
    proc = psutil.Process()
    cpu_before = psutil.cpu_percent(interval=None)
    mem_before = proc.memory_info().rss / (1024**2)
    
    t0 = time.perf_counter()
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        tasks = []
        for i in range(concurrency):
            u = USERS[i % len(USERS)]
            tasks.append(worker_loop(client, u, stop_time, all_results))
        await asyncio.gather(*tasks)
    total_time = time.perf_counter() - t0

    mem_after = proc.memory_info().rss / (1024**2)
    cpu_after = psutil.cpu_percent(interval=None)

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
        "peak_mem_mb": round(mem_after, 2),
        "cpu_pct": cpu_after,
    }

async def main():
    print("=== Running Concurrent User API Load Tests ===")
    concurrency_levels = [1, 10, 25, 50, 100]
    suite_results = []
    
    for c in concurrency_levels:
        print(f"Testing {c:3d} concurrent users (duration: 8s)...")
        res = await run_load_test(concurrency=c, duration_sec=8)
        suite_results.append(res)
        print(f"  -> {c:3d} Users: {res['rps']} RPS | Avg: {res['avg_latency_ms']}ms | p95: {res['p95_latency_ms']}ms | p99: {res['p99_latency_ms']}ms | Errors: {res['failed_requests']} ({res['error_rate_pct']}%)")

    with open("scratch/benchmarks/concurrency_benchmark_results.json", "w") as f:
        json.dump(suite_results, f, indent=2)
    print("\nSaved results to scratch/benchmarks/concurrency_benchmark_results.json")

if __name__ == "__main__":
    asyncio.run(main())

