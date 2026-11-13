import sys
import os
import time
import uuid
import psutil
import json
from datetime import date, time as dtime

sys.path.insert(0, os.path.abspath("backend"))

from app.modules.roster.engine import (
    AutomatedConflictResolver,
    DemandSlot,
    TimeInterval,
    EmployeeSpec,
    OperatingPatternSpec,
    PreferenceSpec,
    PrimaryAssignmentSpec,
    HolidayBehavior,
    ResolverStatus,
)

def benchmark_resolver():
    print("=== Benchmarking CP-SAT Automated Conflict Resolver ===")
    d1 = date(2026, 11, 2)
    pod_a = uuid.uuid4()
    pod_b = uuid.uuid4()
    proc1 = uuid.uuid4()
    proc2 = uuid.uuid4()
    bp1 = uuid.uuid4()
    bp2 = uuid.uuid4()

    patterns = {
        bp1: OperatingPatternSpec(
            brand_process_id=bp1,
            operating_days=(0, 1, 2, 3, 4, 5),
            start_time=dtime(9, 0),
            end_time=dtime(18, 0),
            min_staffing_weekday=1,
            min_staffing_weekend=1,
            holiday_behavior=HolidayBehavior.REDUCED,
            min_staffing_holiday=1,
        ),
        bp2: OperatingPatternSpec(
            brand_process_id=bp2,
            operating_days=(0, 1, 2, 3, 4, 5),
            start_time=dtime(9, 0),
            end_time=dtime(18, 0),
            min_staffing_weekday=1,
            min_staffing_weekend=1,
            holiday_behavior=HolidayBehavior.REDUCED,
            min_staffing_holiday=1,
        ),
    }

    results = []
    for num_slots in [1, 5, 20, 50]:
        # Create pool of employees
        num_emps = max(num_slots * 2, 10)
        employees = {}
        for i in range(num_emps):
            e_id = uuid.uuid4()
            pod_id = pod_a if i % 2 == 0 else pod_b
            employees[e_id] = EmployeeSpec(
                id=e_id,
                name=f"Worker {i+1}",
                email=f"worker{i+1}@bench.io",
                pod_id=pod_id,
                daily_capacity_minutes=540,
                standard_start_time=dtime(9, 0),
                standard_end_time=dtime(18, 0),
                skill_process_ids=(proc1, proc2),
                is_active=True,
            )

        demand_slots = []
        for i in range(num_slots):
            demand_slots.append(DemandSlot(
                brand_process_id=bp1 if i % 2 == 0 else bp2,
                brand_id=uuid.uuid4(),
                process_id=proc1 if i % 2 == 0 else proc2,
                date=d1,
                interval=TimeInterval(start_time=dtime(9, 0), end_time=dtime(18, 0)),
                required_staff=1,
                is_operating=True,
                resolution_source="BENCHMARK",
            ))

        bp_list = [(bp1, uuid.uuid4(), proc1), (bp2, uuid.uuid4(), proc2)]
        bp_pod = {bp1: pod_a, bp2: pod_b}

        t0 = time.perf_counter()
        res = AutomatedConflictResolver.solve(
            target_dates=[d1],
            demand_slots=demand_slots,
            employees=employees,
            patterns=patterns,
            overrides={},
            company_holidays=set(),
            primary_assignments=[],
            unavailabilities={},
            preferences={},
            existing_allocations=[],
            existing_shifts=[],
            brand_processes=bp_list,
            bp_pod_map=bp_pod,
            time_limit_seconds=5.0,
        )
        t_solve = time.perf_counter() - t0
        
        status_name = res.overall_status.name if hasattr(res.overall_status, "name") else str(res.overall_status)
        results.append({
            "num_slots": num_slots,
            "num_candidate_employees": num_emps,
            "solver_status": status_name,
            "duration_sec": round(t_solve, 4),
            "allocated_count": len(res.proposed_allocations) if hasattr(res, "proposed_allocations") else 0,
            "solve_duration_internal": res.solve_duration_seconds,
        })
        print(f"  -> Slots: {num_slots:2d}, Candidates: {num_emps:2d} | Status: {status_name} | Duration: {t_solve:.4f}s (Internal solve: {res.solve_duration_seconds:.4f}s)")

    with open("scratch/benchmarks/resolver_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    benchmark_resolver()
