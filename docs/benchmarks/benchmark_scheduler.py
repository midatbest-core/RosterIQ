import sys
import os
import time
import uuid
import psutil
import json
from datetime import date, time as dtime
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.roster.engine import (
    DeterministicScheduler,
    IndependentValidator,
    EmployeeSpec,
    OperatingPatternSpec,
    OperatingOverrideSpec,
    UnavailabilitySpec,
    PreferenceSpec,
    PrimaryAssignmentSpec,
    HolidayBehavior,
)

def create_dataset(num_employees: int, num_pods: int, num_brands: int, num_processes: int):
    # Pods
    pod_ids = [uuid.uuid4() for _ in range(num_pods)]
    
    # Processes
    proc_ids = [uuid.uuid4() for _ in range(num_processes)]
    
    # Brands
    brand_ids = [uuid.uuid4() for _ in range(num_brands)]
    
    # Brand Processes: map brands to 1-2 processes
    brand_processes = []
    patterns = {}
    for i, b_id in enumerate(brand_ids):
        # 80% single process, 20% two processes
        p_count = 2 if i % 5 == 0 else 1
        for p_idx in range(p_count):
            p_id = proc_ids[(i + p_idx) % num_processes]
            bp_id = uuid.uuid4()
            brand_processes.append((bp_id, b_id, p_id))
            
            # Operating pattern: Mon-Sat (0..5), some Sunday (0..6)
            op_days = (0, 1, 2, 3, 4, 5, 6) if i % 7 == 0 else (0, 1, 2, 3, 4, 5)
            patterns[bp_id] = OperatingPatternSpec(
                brand_process_id=bp_id,
                operating_days=op_days,
                start_time=dtime(9, 0),
                end_time=dtime(18, 0),
                min_staffing_weekday=1,
                min_staffing_weekend=1,
                holiday_behavior=HolidayBehavior.REDUCED,
                min_staffing_holiday=1,
            )
            
    # Employees
    employees = {}
    primary_assignments = []
    preferences = {}
    unavailabilities = {}
    
    for i in range(num_employees):
        e_id = uuid.uuid4()
        pod_id = pod_ids[i % num_pods]
        # Assign 2-3 skills per employee
        skills = tuple(proc_ids[k % num_processes] for k in range(i, i + 3))
        employees[e_id] = EmployeeSpec(
            id=e_id,
            name=f"Worker {i+1}",
            email=f"worker{i+1}@bench.io",
            pod_id=pod_id,
            daily_capacity_minutes=540,
            standard_start_time=dtime(9, 0),
            standard_end_time=dtime(18, 0),
            skill_process_ids=skills,
            is_active=True,
        )
        # Primary assignment to a brand-process
        assigned_bp = brand_processes[i % len(brand_processes)]
        primary_assignments.append(PrimaryAssignmentSpec(
            employee_id=e_id,
            brand_process_id=assigned_bp[0],
            priority=1,
            effective_from=date(2026, 11, 1),
            effective_to=date(2026, 11, 30),
        ))
        # Preferences: weekly off Sunday (6) or Saturday (5)
        pref_off = (6,) if i % 2 == 0 else (5,)
        preferences[e_id] = PreferenceSpec(employee_id=e_id, preferred_weekly_off_days=pref_off)
        
        # 10% employees have 1 day of approved leave
        if i % 10 == 0:
            unavailabilities[(e_id, date(2026, 11, 15))] = UnavailabilitySpec(
                employee_id=e_id,
                date=date(2026, 11, 15),
                reason_type="PLANNED_LEAVE",
                is_approved=True,
            )
            
    # Overrides and Holidays
    overrides = {}
    company_holidays = {date(2026, 11, 26)} # Thanksgiving holiday
    
    return {
        "brand_processes": brand_processes,
        "patterns": patterns,
        "overrides": overrides,
        "company_holidays": company_holidays,
        "employees": employees,
        "primary_assignments": primary_assignments,
        "unavailabilities": unavailabilities,
        "preferences": preferences,
    }

def run_single_scheduler_benchmark(ds_name: str, ds: dict):
    process = psutil.Process()
    mem_before = process.memory_info().rss / (1024**2)
    t0 = time.perf_counter()
    
    result = DeterministicScheduler.generate_monthly_roster(
        year=2026,
        month=11,
        brand_processes=ds["brand_processes"],
        patterns=ds["patterns"],
        overrides=ds["overrides"],
        company_holidays=ds["company_holidays"],
        employees=ds["employees"],
        primary_assignments=ds["primary_assignments"],
        unavailabilities=ds["unavailabilities"],
        preferences=ds["preferences"],
    )
    t_gen = time.perf_counter() - t0
    mem_after = process.memory_info().rss / (1024**2)
    mem_delta = mem_after - mem_before
    
    # Run independent validator
    all_dates = [date(2026, 11, d) for d in range(1, 31)]
    t_v0 = time.perf_counter()
    conflicts = IndependentValidator.validate_roster(
        all_dates=all_dates,
        brand_processes=ds["brand_processes"],
        patterns=ds["patterns"],
        overrides=ds["overrides"],
        company_holidays=ds["company_holidays"],
        employees=ds["employees"],
        unavailabilities=ds["unavailabilities"],
        shifts=result.shifts,
        allocations=result.allocations,
    )
    t_val = time.perf_counter() - t_v0
    
    hard_conflicts = [c for c in conflicts if c.severity.name == "HARD"]
    soft_conflicts = [c for c in conflicts if c.severity.name == "SOFT"]
    
    return {
        "dataset": ds_name,
        "num_employees": len(ds["employees"]),
        "num_brand_processes": len(ds["brand_processes"]),
        "gen_duration_sec": round(t_gen, 4),
        "val_duration_sec": round(t_val, 4),
        "total_duration_sec": round(t_gen + t_val, 4),
        "shifts_count": len(result.shifts),
        "allocations_count": len(result.allocations),
        "hard_conflicts": len(hard_conflicts),
        "soft_conflicts": len(soft_conflicts),
        "total_conflicts": len(conflicts),
        "peak_mem_mb": round(mem_after, 2),
        "mem_delta_mb": round(mem_delta, 2),
    }

def run_concurrent_scheduler_benchmark(ds: dict, concurrency: int):
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                DeterministicScheduler.generate_monthly_roster,
                year=2026,
                month=11,
                brand_processes=ds["brand_processes"],
                patterns=ds["patterns"],
                overrides=ds["overrides"],
                company_holidays=ds["company_holidays"],
                employees=ds["employees"],
                primary_assignments=ds["primary_assignments"],
                unavailabilities=ds["unavailabilities"],
                preferences=ds["preferences"],
            )
            for _ in range(concurrency)
        ]
        results = [f.result() for f in futures]
    t_total = time.perf_counter() - t0
    return {
        "concurrency": concurrency,
        "total_time_sec": round(t_total, 4),
        "throughput_runs_per_sec": round(concurrency / t_total, 2),
        "avg_time_per_run_sec": round(t_total / concurrency, 4),
    }

def main():
    print("=== Running Scheduler Engine Benchmarks ===")
    
    datasets = {
        "A_Current": create_dataset(36, 4, 15, 5),
        "B_Medium": create_dataset(100, 10, 40, 10),
        "C_Larger": create_dataset(300, 20, 100, 15),
    }
    
    scale_results = []
    for name, ds in datasets.items():
        print(f"Benchmarking {name} ({len(ds['employees'])} employees, {len(ds['brand_processes'])} BPs)...")
        res = run_single_scheduler_benchmark(name, ds)
        scale_results.append(res)
        print(f"  -> Gen Time: {res['gen_duration_sec']}s, Val Time: {res['val_duration_sec']}s, Total: {res['total_duration_sec']}s, Allocations: {res['allocations_count']}, Hard Conflicts: {res['hard_conflicts']}")
        
    print("\n=== Running Concurrent Generation Benchmark (Dataset A) ===")
    concurrency_levels = [1, 2, 5, 10]
    concurrent_results = []
    for c in concurrency_levels:
        c_res = run_concurrent_scheduler_benchmark(datasets["A_Current"], c)
        concurrent_results.append(c_res)
        print(f"  -> Concurrency {c}: Total {c_res['total_time_sec']}s ({c_res['throughput_runs_per_sec']} runs/s)")
        
    out = {
        "scale_benchmarks": scale_results,
        "concurrent_benchmarks": concurrent_results,
    }
    with open("scratch/benchmarks/scheduler_benchmark_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nSaved results to scratch/benchmarks/scheduler_benchmark_results.json")

if __name__ == "__main__":
    main()
