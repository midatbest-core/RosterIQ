import sys
import os
import time
import json
import statistics
import concurrent.futures
from uuid import uuid4

sys.path.insert(0, os.path.abspath("backend"))

BENCH_DB_PATH = os.path.abspath("scratch/benchmarks/bench_isolated.db")
BENCH_DB_URL = f"sqlite+pysqlite:///{BENCH_DB_PATH.replace(os.sep, '/')}"

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

import app.db.models
from app.modules.auth.models import User
from app.modules.workforce.models import Employee
from app.modules.roster.models import Roster, RosterAllocation, EmployeeShift

def benchmark_database_operations():
    print("=== Running Database Operations & Pool Micro-Benchmark ===")
    
    # 1. Measure with tuned QueuePool
    engine = create_engine(
        BENCH_DB_URL,
        poolclass=QueuePool,
        pool_size=50,
        max_overflow=50,
        pool_timeout=10.0,
        connect_args={"check_same_thread": False, "timeout": 30}
    )
    Session = sessionmaker(bind=engine)

    results = {}

    # Read Benchmark: Single Row by PK
    with Session() as s:
        emp = s.scalars(select(Employee)).first()
        emp_id = emp.id if emp else None

    pk_latencies = []
    for _ in range(500):
        t0 = time.perf_counter()
        with Session() as s:
            e = s.get(Employee, emp_id)
        pk_latencies.append((time.perf_counter() - t0) * 1000.0)
    
    pk_latencies.sort()
    results["single_pk_lookup"] = {
        "iterations": len(pk_latencies),
        "avg_ms": round(statistics.mean(pk_latencies), 3),
        "median_ms": round(statistics.median(pk_latencies), 3),
        "p95_ms": round(pk_latencies[int(len(pk_latencies)*0.95)], 3),
        "p99_ms": round(pk_latencies[int(len(pk_latencies)*0.99)], 3),
    }

    # Complex Join Query: Roster with Shifts & Allocations
    join_latencies = []
    for _ in range(200):
        t0 = time.perf_counter()
        with Session() as s:
            stmt = (
                select(EmployeeShift, RosterAllocation)
                .join(RosterAllocation, RosterAllocation.employee_id == EmployeeShift.employee_id)
                .limit(100)
            )
            rows = s.execute(stmt).all()
        join_latencies.append((time.perf_counter() - t0) * 1000.0)

    join_latencies.sort()
    results["complex_join_query"] = {
        "iterations": len(join_latencies),
        "avg_ms": round(statistics.mean(join_latencies), 3),
        "median_ms": round(statistics.median(join_latencies), 3),
        "p95_ms": round(join_latencies[int(len(join_latencies)*0.95)], 3),
        "p99_ms": round(join_latencies[int(len(join_latencies)*0.99)], 3),
    }

    # Write Transaction: Insert & Commit Record
    write_latencies = []
    for i in range(100):
        t0 = time.perf_counter()
        with Session() as s:
            u = User(
                id=uuid4(),
                email=f"bench_temp_{i}_{uuid4().hex[:6]}@bench.io",
                password_hash="hash",
                role="EMPLOYEE",
                is_active=True
            )
            s.add(u)
            s.commit()
        write_latencies.append((time.perf_counter() - t0) * 1000.0)

    write_latencies.sort()
    results["single_insert_commit"] = {
        "iterations": len(write_latencies),
        "avg_ms": round(statistics.mean(write_latencies), 3),
        "median_ms": round(statistics.median(write_latencies), 3),
        "p95_ms": round(write_latencies[int(len(write_latencies)*0.95)], 3),
        "p99_ms": round(write_latencies[int(len(write_latencies)*0.99)], 3),
    }

    # Concurrent Pool Checkout Test under Thread Contention
    def checkout_worker():
        t0 = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return (time.perf_counter() - t0) * 1000.0

    pool_scaling = {}
    for threads in [10, 25, 50, 100]:
        t0 = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futs = [executor.submit(checkout_worker) for _ in range(threads * 10)]
            thread_lats = [f.result() for f in concurrent.futures.as_completed(futs)]
        elapsed = time.perf_counter() - t0
        thread_lats.sort()
        pool_scaling[f"{threads}_threads"] = {
            "total_queries": len(thread_lats),
            "total_time_s": round(elapsed, 3),
            "qps": round(len(thread_lat) / elapsed, 1) if (thread_lat := thread_lats) and elapsed > 0 else 0,
            "avg_checkout_ms": round(statistics.mean(thread_lats), 3),
            "p95_checkout_ms": round(thread_lats[int(len(thread_lats)*0.95)], 3),
            "p99_checkout_ms": round(thread_lats[int(len(thread_lats)*0.99)], 3),
        }

    results["pool_concurrency_scaling"] = pool_scaling

    with open("scratch/benchmarks/db_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Saved DB benchmark results to scratch/benchmarks/db_benchmark_results.json")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    benchmark_database_operations()
