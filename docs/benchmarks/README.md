# RosterIQ Benchmark Suite

This directory contains the reproducible benchmark harness scripts, workload generators, and raw JSON result payloads used for the Stage 8.1 Performance Audit of RosterIQ.

---

## 1. Directory Contents

| File | Purpose | Workload / Scope |
| :--- | :--- | :--- |
| `benchmark_scheduler.py` | Standalone benchmark of the deterministic roster generator and independent validator | Tests Dataset A (36 emps), Dataset B (100 emps), and Dataset C (300 emps) for 30 days (Nov 2026). Measures generation time, validation time, shift counts, and conflicts. |
| `benchmark_resolver.py` | Google OR-Tools CP-SAT conflict resolver micro-benchmark | Tests single-slot disruption with 10 candidate workers. Measures internal solver solve time and proposed allocation count. |
| `run_concurrent_benchmark.py` | Multi-role concurrent authenticated journey benchmark | Simulates 1, 10, 25, 50, and 100 concurrent users cycling through realistic endpoints across all 5 user roles via in-memory `httpx.ASGITransport`. |
| `benchmark_sse.py` | In-memory event bus (`NotificationBroadcaster`) micro-benchmark | Measures subscriber queue registration, memory footprint, and fanout multicast dispatch latency across 25 to 200 queues. |
| `benchmark_db.py` | Database operation micro-benchmarks on local SQLite | Measures PK lookup, multi-table join, transaction commit, and thread pool checkout contention. |
| `setup_benchmark_db.py` | Database seeder for standalone micro-benchmarks | Initializes the benchmark schema and populates test records. |
| `scheduler_benchmark_results.json` | Raw output from `benchmark_scheduler.py` | Machine-readable metrics for Dataset A, B, and C. |
| `resolver_benchmark_results.json` | Raw output from `benchmark_resolver.py` | Machine-readable metrics for CP-SAT resolver. |
| `concurrency_benchmark_results.json` | Raw output from `run_concurrent_benchmark.py` | Machine-readable metrics for ASGI concurrent user runs. |
| `sse_benchmark_results.json` | Raw output from `benchmark_sse.py` | Machine-readable metrics for in-memory broker. |
| `db_benchmark_results.json` | Raw output from `benchmark_db.py` | Machine-readable metrics for local SQLite latency. |

---

## 2. Reproduction Instructions

All benchmarks require Python 3.11+ (tested on Python 3.14.3) and the backend dependencies.

### Step 1: Activate Environment & Set PYTHONPATH
```powershell
Set-Location C:\Users\Admin\Roster
$env:PYTHONPATH = "C:\Users\Admin\Roster\backend"
```

### Step 2: Run Scheduling Engine Benchmark
```powershell
python docs/benchmarks/benchmark_scheduler.py
```
*Expected Output for Dataset A:* ~28-35 ms total compute, 470 shifts, 0 conflicts.

### Step 3: Run CP-SAT Conflict Resolver Benchmark
```powershell
python docs/benchmarks/benchmark_resolver.py
```
*Expected Output:* Status `OPTIMAL`, solve duration ~45-55 ms, 1 allocation proposed.

### Step 4: Run Real-Time In-Memory Bus Benchmark
```powershell
python docs/benchmarks/benchmark_sse.py
```
*Expected Output:* Fanout dispatch to 200 queues in ~0.8-1.0 ms (>200,000 events/sec).

### Step 5: Run Database Micro-Benchmarks
```powershell
python docs/benchmarks/benchmark_db.py
```
*Expected Output:* PK lookup ~0.25 ms, complex join ~1.68 ms, commit ~4.08 ms.

---

## 3. Disclosures & Scope Limitations

1. **In-Process Isolation**: The ASGI concurrency tests use `httpx.ASGITransport(app=app)` to measure pure application CPU and serialization overhead without TCP, TLS, or public internet routing.
2. **Local Database Isolation**: Micro-benchmarks use an isolated SQLite 3 file in WAL mode to guarantee zero disruption to the staging Neon PostgreSQL database.
3. **Multi-Slot Resolver Retraction**: Solver capacity was measured on a single disrupted slot. Previous multi-slot synthetic tests with duplicated slot keys have been retracted.
