import sys
import os
import time
import asyncio
import psutil
import json
import statistics
from uuid import uuid4
import httpx

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.auth.broadcaster import broadcaster

async def run_sse_benchmark():
    print("=== Running SSE (Server-Sent Events) Concurrency Benchmark ===")
    
    proc = psutil.Process()
    concurrency_levels = [25, 50, 100, 200]
    results = []

    for c in concurrency_levels:
        mem_before = proc.memory_info().rss / (1024**2)
        user_ids = [uuid4() for _ in range(c)]
        
        # 1. Connection establishment benchmark
        t0 = time.perf_counter()
        queues = []
        for uid in user_ids:
            q = await broadcaster.subscribe(uid)
            queues.append((uid, q))
        connect_time_ms = (time.perf_counter() - t0) * 1000.0
        avg_connect_lat = connect_time_ms / c

        mem_after_connect = proc.memory_info().rss / (1024**2)
        mem_per_client_kb = ((mem_after_connect - mem_before) * 1024) / c if c > 0 else 0

        # 2. Targeted broadcast latency
        # Send an event to each user and measure delivery time
        delivery_latencies_ms = []
        for uid, q in queues:
            test_payload = {"event": "notification", "id": str(uuid4()), "ts": time.perf_counter()}
            t_pub = time.perf_counter()
            await broadcaster.publish(uid, test_payload)
            item = await asyncio.wait_for(q.get(), timeout=1.0)
            lat = (time.perf_counter() - t_pub) * 1000.0
            delivery_latencies_ms.append(lat)

        # 3. Multi-cast / pod broadcast simulation (publish to all connected users)
        t_multi = time.perf_counter()
        broadcast_tasks = [broadcaster.publish(uid, {"type": "BROADCAST", "seq": i}) for i, (uid, _) in enumerate(queues)]
        await asyncio.gather(*broadcast_tasks)
        multi_lat_ms = (time.perf_counter() - t_multi) * 1000.0

        # Cleanup
        for uid, q in queues:
            await broadcaster.unsubscribe(uid, q)

        mem_after_cleanup = proc.memory_info().rss / (1024**2)

        avg_delivery = statistics.mean(delivery_latencies_ms)
        p95_delivery = sorted(delivery_latencies_ms)[int(len(delivery_latencies_ms) * 0.95)]
        max_delivery = max(delivery_latencies_ms)

        res = {
            "concurrent_subscribers": c,
            "total_subscribe_time_ms": round(connect_time_ms, 2),
            "avg_connect_latency_ms": round(avg_connect_lat, 4),
            "memory_before_mb": round(mem_before, 2),
            "memory_after_mb": round(mem_after_connect, 2),
            "mem_overhead_kb_per_client": round(mem_per_client_kb, 2),
            "delivery_avg_ms": round(avg_delivery, 4),
            "delivery_p95_ms": round(p95_delivery, 4),
            "delivery_max_ms": round(max_delivery, 4),
            "fanout_total_time_ms": round(multi_lat_ms, 2),
            "fanout_throughput_events_per_sec": round((c / (multi_lat_ms / 1000.0)), 1) if multi_lat_ms > 0 else 0
        }
        results.append(res)
        print(f"  -> {c:3d} SSE Clients | Avg Connect: {res['avg_connect_latency_ms']}ms | Fanout: {res['fanout_total_time_ms']}ms ({res['fanout_throughput_events_per_sec']} ev/s) | Delivery p95: {res['delivery_p95_ms']}ms | Mem/client: {res['mem_overhead_kb_per_client']} KB")

    with open("scratch/benchmarks/sse_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved SSE benchmark results to scratch/benchmarks/sse_benchmark_results.json")

if __name__ == "__main__":
    asyncio.run(run_sse_benchmark())

