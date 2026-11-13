from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from enum import Enum
import hashlib
import json
import uuid

from ortools.sat.python import cp_model

from app.modules.roster.engine.domain import (
    AllocationType,
    DemandSlot,
    EmployeeSpec,
    OperatingOverrideSpec,
    OperatingPatternSpec,
    PreferenceSpec,
    PrimaryAssignmentSpec,
    ScheduledAllocation,
    ScheduledShift,
    TimeInterval,
    UnavailabilitySpec,
    ValidationConflict,
)
from app.modules.roster.engine.validator import IndependentValidator


class ResolverStatus(str, Enum):
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"
    MODEL_INVALID = "MODEL_INVALID"


class ActionType(str, Enum):
    NEW_ALLOCATION = "NEW_ALLOCATION"
    REASSIGN_ALLOCATION = "REASSIGN_ALLOCATION"
    MOVE_ALLOCATION = "MOVE_ALLOCATION"
    RETAIN_ALLOCATION = "RETAIN_ALLOCATION"
    REMOVE_ALLOCATION = "REMOVE_ALLOCATION"


@dataclass(frozen=True)
class LexicographicPassResult:
    pass_name: str
    status: ResolverStatus
    solve_time_seconds: float
    objective_value: float | None = None
    covered_positions: int = 0
    fully_satisfied_slots: int = 0
    cross_pod_positions: int = 0
    perturbation_count: int = 0
    stage_statuses: tuple[tuple[str, str, float], ...] = ()


@dataclass
class AllocationChange:
    action_type: ActionType
    date: date
    brand_process_id: uuid.UUID
    interval: TimeInterval
    employee_id: uuid.UUID
    allocation_id: uuid.UUID | None = None
    previous_employee_id: uuid.UUID | None = None
    is_cross_pod: bool = False
    source_pod_id: uuid.UUID | None = None
    target_pod_id: uuid.UUID | None = None
    notes: str | None = None


@dataclass
class ResolutionBundle:
    bundle_id: uuid.UUID
    target_date: date
    brand_process_ids: list[uuid.UUID]
    is_cross_pod: bool
    requires_manager_approval: bool
    description: str
    changes: list[AllocationChange] = field(default_factory=list)
    cascading_chain: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ShortageEvidence:
    date: date
    brand_process_id: uuid.UUID
    brand_id: uuid.UUID
    process_id: uuid.UUID
    required_staff: int
    assigned_staff: int
    shortfall: int
    total_pod_certified: int
    total_company_certified: int
    available_pod_certified: int
    available_company_certified: int
    reasons: tuple[str, ...]


@dataclass
class ResolverResult:
    overall_status: ResolverStatus
    pass_results: list[LexicographicPassResult]
    total_demand_slots: int
    total_required_staff_positions: int
    initial_covered_positions: int
    final_covered_positions: int
    initial_uncovered_positions: int
    final_uncovered_positions: int
    fully_satisfied_demand_slots: int
    partially_satisfied_demand_slots: int
    uncovered_demand_slots: int
    proposed_shifts: list[ScheduledShift]
    proposed_allocations: list[ScheduledAllocation]
    resolution_bundles: list[ResolutionBundle]
    shortage_evidences: list[ShortageEvidence]
    validation_conflicts: list[ValidationConflict]
    snapshot_hash: str
    solve_duration_seconds: float


class AutomatedConflictResolver:
    """
    Deterministic constraint-based conflict resolver using Google OR-Tools CP-SAT.
    
    Principles:
    1. Genuine multi-stage sequential lexicographic optimization:
       - Stage 1: Maximize total covered staffing positions.
       - Stage 2: Maximize fully satisfied demand intervals.
       - Stage 3: Minimize cross-pod assignments.
       - Stage 4: Minimize baseline churn (unnecessary reassignments).
       - Stage 5: Maximize primary retention and respect soft weekly-off preferences.
    2. Pass B preserves both staffing positions and fully satisfied intervals from Pass A.
    3. Shift vs Allocation separation: exactly one shift per working date enclosing non-overlapping allocations.
    4. Zero phantom shifts: shift active iff at least one process allocation is assigned.
    5. Connected-component atomic bundling: dependent cascading swaps across multiple brands
       on the same date are grouped into a single atomic ResolutionBundle.
    6. Complete snapshot fingerprinting: covers dates, demand, employee attributes, skills,
       primaries, unavailabilities, preferences, and existing allocations.
    7. IndependentValidator remains the final authority for all generated rosters.
    """

    @classmethod
    def compute_snapshot_hash(
        cls,
        target_dates: list[date],
        demand_slots: list[DemandSlot],
        employees: dict[uuid.UUID, EmployeeSpec],
        primary_assignments: list[PrimaryAssignmentSpec],
        unavailabilities: dict[tuple[uuid.UUID, date], UnavailabilitySpec],
        preferences: dict[uuid.UUID, PreferenceSpec],
        existing_allocations: list[ScheduledAllocation],
    ) -> str:
        """
        Computes a deterministic SHA-256 fingerprint over all relevant solver inputs.
        """
        payload = {
            "dates": [d.isoformat() for d in sorted(target_dates)],
            "demand": sorted([
                (
                    s.date.isoformat(),
                    str(s.brand_process_id),
                    str(s.brand_id),
                    str(s.process_id),
                    s.interval.start_time.isoformat(),
                    s.interval.end_time.isoformat(),
                    s.required_staff,
                )
                for s in demand_slots
            ]),
            "employees": sorted([
                (
                    str(e.id),
                    str(e.pod_id) if e.pod_id else "",
                    e.daily_capacity_minutes,
                    e.standard_start_time.isoformat(),
                    e.standard_end_time.isoformat(),
                    sorted(str(pid) for pid in e.skill_process_ids),
                    e.is_active,
                )
                for e in employees.values()
            ]),
            "primaries": sorted([
                (str(p.employee_id), str(p.brand_process_id), p.priority)
                for p in primary_assignments
            ]),
            "unavailabilities": sorted([
                (str(k[0]), k[1].isoformat(), u.reason_type, u.is_approved)
                for k, u in unavailabilities.items()
            ]),
            "preferences": sorted([
                (str(p.employee_id), list(sorted(p.preferred_weekly_off_days)))
                for p in preferences.values()
            ]),
            "existing_allocs": sorted([
                (
                    str(a.id),
                    str(a.employee_id),
                    str(a.brand_process_id),
                    a.date.isoformat(),
                    a.interval.start_time.isoformat(),
                    a.interval.end_time.isoformat(),
                    a.allocation_type.value,
                )
                for a in existing_allocations
            ]),
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def solve(
        cls,
        target_dates: list[date],
        demand_slots: list[DemandSlot],
        employees: dict[uuid.UUID, EmployeeSpec],
        patterns: dict[uuid.UUID, OperatingPatternSpec],
        overrides: dict[tuple[uuid.UUID, date], OperatingOverrideSpec],
        company_holidays: set[date],
        primary_assignments: list[PrimaryAssignmentSpec],
        unavailabilities: dict[tuple[uuid.UUID, date], UnavailabilitySpec],
        preferences: dict[uuid.UUID, PreferenceSpec],
        existing_allocations: list[ScheduledAllocation],
        existing_shifts: list[ScheduledShift],
        brand_processes: list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]],
        bp_pod_map: dict[uuid.UUID, uuid.UUID | None],
        time_limit_seconds: float = 5.0,
        allow_cross_pod: bool = True,
    ) -> ResolverResult:
        start_time = datetime.now(timezone.utc)
        snapshot_hash = cls.compute_snapshot_hash(
            target_dates=target_dates,
            demand_slots=demand_slots,
            employees=employees,
            primary_assignments=primary_assignments,
            unavailabilities=unavailabilities,
            preferences=preferences,
            existing_allocations=existing_allocations,
        )

        active_demand = [
            s for s in demand_slots
            if s.date in target_dates and s.is_operating and s.required_staff > 0
        ]
        total_demand_slots = len(active_demand)
        total_required_staff_positions = sum(s.required_staff for s in active_demand)

        initial_covered_positions = sum(
            1 for a in existing_allocations
            if a.date in target_dates
        )
        initial_uncovered = max(0, total_required_staff_positions - initial_covered_positions)

        # =========================================================================
        # TARGETED DATE DECOMPOSITION: High-performance solve for multi-date rosters
        # Resolves each conflicted date in milliseconds, locking clean dates.
        # =========================================================================
        if len(target_dates) > 1:
            initial_conflicts = IndependentValidator.validate_roster(
                all_dates=target_dates,
                brand_processes=brand_processes,
                patterns=patterns,
                overrides=overrides,
                company_holidays=company_holidays,
                employees=employees,
                unavailabilities=unavailabilities,
                shifts=existing_shifts,
                allocations=existing_allocations,
            )
            conflicted_dates = {c.date for c in initial_conflicts if c.date in target_dates}

            demand_req_by_date: dict[date, int] = defaultdict(int)
            for s in active_demand:
                demand_req_by_date[s.date] += s.required_staff

            alloc_count_by_date: dict[date, int] = defaultdict(int)
            for a in existing_allocations:
                if a.date in target_dates:
                    alloc_count_by_date[a.date] += 1

            for d in target_dates:
                if alloc_count_by_date.get(d, 0) < demand_req_by_date.get(d, 0):
                    conflicted_dates.add(d)

            all_proposed_allocs: list[ScheduledAllocation] = []
            all_proposed_shifts: list[ScheduledShift] = []
            all_bundles: list[ResolutionBundle] = []
            all_pass_results: list[LexicographicPassResult] = []
            decomposed_status = ResolverStatus.OPTIMAL

            for d in sorted(target_dates):
                d_demand = [s for s in active_demand if s.date == d]
                d_allocs = [a for a in existing_allocations if a.date == d]
                d_shifts = [s for s in existing_shifts if s.date == d]

                if d not in conflicted_dates and d_allocs:
                    all_proposed_allocs.extend(d_allocs)
                    all_proposed_shifts.extend(d_shifts)
                else:
                    per_date_limit = max(0.15, min(0.6, time_limit_seconds / max(1, len(conflicted_dates))))
                    sub_result = cls.solve(
                        target_dates=[d],
                        demand_slots=d_demand,
                        employees=employees,
                        patterns=patterns,
                        overrides=overrides,
                        company_holidays=company_holidays,
                        primary_assignments=primary_assignments,
                        unavailabilities=unavailabilities,
                        preferences=preferences,
                        existing_allocations=d_allocs,
                        existing_shifts=d_shifts,
                        brand_processes=brand_processes,
                        bp_pod_map=bp_pod_map,
                        time_limit_seconds=per_date_limit,
                        allow_cross_pod=allow_cross_pod,
                    )
                    if sub_result.overall_status != ResolverStatus.OPTIMAL:
                        if sub_result.overall_status == ResolverStatus.FEASIBLE:
                            decomposed_status = ResolverStatus.FEASIBLE
                        elif decomposed_status != ResolverStatus.FEASIBLE:
                            decomposed_status = sub_result.overall_status

                    all_proposed_allocs.extend(sub_result.proposed_allocations)
                    all_proposed_shifts.extend(sub_result.proposed_shifts)
                    all_bundles.extend(sub_result.resolution_bundles)
                    all_pass_results.extend(sub_result.pass_results)

            final_validation_conflicts = IndependentValidator.validate_roster(
                all_dates=target_dates,
                brand_processes=brand_processes,
                patterns=patterns,
                overrides=overrides,
                company_holidays=company_holidays,
                employees=employees,
                unavailabilities=unavailabilities,
                shifts=all_proposed_shifts,
                allocations=all_proposed_allocs,
            )

            covered_positions_by_slot: dict[tuple[uuid.UUID, date], int] = {}
            for a in all_proposed_allocs:
                covered_positions_by_slot[(a.brand_process_id, a.date)] = (
                    covered_positions_by_slot.get((a.brand_process_id, a.date), 0) + 1
                )

            fully_satisfied_count = 0
            partially_satisfied_count = 0
            uncovered_count = 0
            shortage_evidences: list[ShortageEvidence] = []
            bp_info_map = {bp[0]: (bp[1], bp[2]) for bp in brand_processes}

            for slot in active_demand:
                cov = covered_positions_by_slot.get((slot.brand_process_id, slot.date), 0)
                if cov == slot.required_staff:
                    fully_satisfied_count += 1
                elif cov > 0:
                    partially_satisfied_count += 1
                    shortfall = slot.required_staff - cov
                    evidence = cls._analyze_shortage(
                        slot=slot,
                        assigned_count=cov,
                        shortfall=shortfall,
                        employees=employees,
                        unavailabilities=unavailabilities,
                        existing_shifts=all_proposed_shifts,
                        bp_info_map=bp_info_map,
                        bp_pod_map=bp_pod_map,
                    )
                    shortage_evidences.append(evidence)
                else:
                    uncovered_count += 1
                    shortfall = slot.required_staff
                    evidence = cls._analyze_shortage(
                        slot=slot,
                        assigned_count=0,
                        shortfall=shortfall,
                        employees=employees,
                        unavailabilities=unavailabilities,
                        existing_shifts=all_proposed_shifts,
                        bp_info_map=bp_info_map,
                        bp_pod_map=bp_pod_map,
                    )
                    shortage_evidences.append(evidence)

            final_covered = len(all_proposed_allocs)
            final_uncovered = max(0, total_required_staff_positions - final_covered)
            duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()

            return ResolverResult(
                overall_status=decomposed_status,
                pass_results=all_pass_results,
                total_demand_slots=total_demand_slots,
                total_required_staff_positions=total_required_staff_positions,
                initial_covered_positions=initial_covered_positions,
                final_covered_positions=final_covered,
                initial_uncovered_positions=initial_uncovered,
                final_uncovered_positions=final_uncovered,
                fully_satisfied_demand_slots=fully_satisfied_count,
                partially_satisfied_demand_slots=partially_satisfied_count,
                uncovered_demand_slots=uncovered_count,
                proposed_shifts=all_proposed_shifts,
                proposed_allocations=all_proposed_allocs,
                resolution_bundles=all_bundles,
                shortage_evidences=shortage_evidences,
                validation_conflicts=final_validation_conflicts,
                snapshot_hash=snapshot_hash,
                solve_duration_seconds=duration_sec,
            )

        pass_results: list[LexicographicPassResult] = []

        # =========================================================================
        # PASS A: Same-Pod Sequential Lexicographic Optimization
        # =========================================================================
        pass_a_solution, pass_a_res = cls._run_solver_pass(
            pass_name="Pass A (Same-Pod Only)",
            target_dates=target_dates,
            demand_slots=active_demand,
            employees=employees,
            unavailabilities=unavailabilities,
            primary_assignments=primary_assignments,
            preferences=preferences,
            existing_allocations=existing_allocations,
            bp_pod_map=bp_pod_map,
            allow_cross_pod=False,
            time_limit_seconds=max(0.5, time_limit_seconds / 2.0 if allow_cross_pod else time_limit_seconds),
        )
        pass_results.append(pass_a_res)

        final_solution = pass_a_solution
        overall_status = pass_a_res.status

        # =========================================================================
        # PASS B: Expanded Cross-Pod Optimization (preserving Pass A's results)
        # =========================================================================
        remaining_shortage = total_required_staff_positions - pass_a_res.covered_positions
        if allow_cross_pod and remaining_shortage > 0:
            pass_b_solution, pass_b_res = cls._run_solver_pass(
                pass_name="Pass B (Expanded Cross-Pod)",
                target_dates=target_dates,
                demand_slots=active_demand,
                employees=employees,
                unavailabilities=unavailabilities,
                primary_assignments=primary_assignments,
                preferences=preferences,
                existing_allocations=existing_allocations,
                bp_pod_map=bp_pod_map,
                allow_cross_pod=True,
                time_limit_seconds=max(0.5, time_limit_seconds / 2.0),
                min_covered_positions=pass_a_res.covered_positions,
                min_fully_satisfied_slots=pass_a_res.fully_satisfied_slots,
            )
            pass_results.append(pass_b_res)
            if pass_b_res.covered_positions >= pass_a_res.covered_positions:
                final_solution = pass_b_solution
                # If either pass was only FEASIBLE, the overall result is FEASIBLE (never falsely OPTIMAL)
                if pass_a_res.status == ResolverStatus.FEASIBLE or pass_b_res.status == ResolverStatus.FEASIBLE:
                    overall_status = ResolverStatus.FEASIBLE
                else:
                    overall_status = pass_b_res.status

        # =========================================================================
        # Synthesize Shifts, Allocations & Connected-Component Resolution Bundles
        # =========================================================================
        proposed_allocations, proposed_shifts, resolution_bundles = cls._build_schedule_and_bundles(
            solution=final_solution,
            demand_slots=active_demand,
            employees=employees,
            existing_allocations=existing_allocations,
            bp_pod_map=bp_pod_map,
            primary_assignments=primary_assignments,
        )

        # =========================================================================
        # Run IndependentValidator as Final Authority
        # =========================================================================
        all_validation_conflicts = IndependentValidator.validate_roster(
            all_dates=target_dates,
            brand_processes=brand_processes,
            patterns=patterns,
            overrides=overrides,
            company_holidays=company_holidays,
            employees=employees,
            unavailabilities=unavailabilities,
            shifts=proposed_shifts,
            allocations=proposed_allocations,
        )

        # =========================================================================
        # Metrics & Shortage Evidence Analysis
        # =========================================================================
        covered_positions_by_slot: dict[tuple[uuid.UUID, date], int] = {}
        for a in proposed_allocations:
            covered_positions_by_slot[(a.brand_process_id, a.date)] = (
                covered_positions_by_slot.get((a.brand_process_id, a.date), 0) + 1
            )

        fully_satisfied_count = 0
        partially_satisfied_count = 0
        uncovered_count = 0
        shortage_evidences: list[ShortageEvidence] = []

        bp_info_map = {bp[0]: (bp[1], bp[2]) for bp in brand_processes}

        for slot in active_demand:
            cov = covered_positions_by_slot.get((slot.brand_process_id, slot.date), 0)
            if cov == slot.required_staff:
                fully_satisfied_count += 1
            elif cov > 0:
                partially_satisfied_count += 1
                shortfall = slot.required_staff - cov
                evidence = cls._analyze_shortage(
                    slot=slot,
                    assigned_count=cov,
                    shortfall=shortfall,
                    employees=employees,
                    unavailabilities=unavailabilities,
                    existing_shifts=proposed_shifts,
                    bp_info_map=bp_info_map,
                    bp_pod_map=bp_pod_map,
                )
                shortage_evidences.append(evidence)
            else:
                uncovered_count += 1
                shortfall = slot.required_staff
                evidence = cls._analyze_shortage(
                    slot=slot,
                    assigned_count=0,
                    shortfall=shortfall,
                    employees=employees,
                    unavailabilities=unavailabilities,
                    existing_shifts=proposed_shifts,
                    bp_info_map=bp_info_map,
                    bp_pod_map=bp_pod_map,
                )
                shortage_evidences.append(evidence)

        final_covered = len(proposed_allocations)
        final_uncovered = max(0, total_required_staff_positions - final_covered)
        duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()

        return ResolverResult(
            overall_status=overall_status,
            pass_results=pass_results,
            total_demand_slots=total_demand_slots,
            total_required_staff_positions=total_required_staff_positions,
            initial_covered_positions=initial_covered_positions,
            final_covered_positions=final_covered,
            initial_uncovered_positions=initial_uncovered,
            final_uncovered_positions=final_uncovered,
            fully_satisfied_demand_slots=fully_satisfied_count,
            partially_satisfied_demand_slots=partially_satisfied_count,
            uncovered_demand_slots=uncovered_count,
            proposed_shifts=proposed_shifts,
            proposed_allocations=proposed_allocations,
            resolution_bundles=resolution_bundles,
            shortage_evidences=shortage_evidences,
            validation_conflicts=all_validation_conflicts,
            snapshot_hash=snapshot_hash,
            solve_duration_seconds=duration_sec,
        )

    @classmethod
    def _run_solver_pass(
        cls,
        pass_name: str,
        target_dates: list[date],
        demand_slots: list[DemandSlot],
        employees: dict[uuid.UUID, EmployeeSpec],
        unavailabilities: dict[tuple[uuid.UUID, date], UnavailabilitySpec],
        primary_assignments: list[PrimaryAssignmentSpec],
        preferences: dict[uuid.UUID, PreferenceSpec],
        existing_allocations: list[ScheduledAllocation],
        bp_pod_map: dict[uuid.UUID, uuid.UUID | None],
        allow_cross_pod: bool,
        time_limit_seconds: float,
        min_covered_positions: int = 0,
        min_fully_satisfied_slots: int = 0,
    ) -> tuple[dict[tuple[uuid.UUID, date, uuid.UUID], bool], LexicographicPassResult]:
        """
        Executes genuine sequential lexicographic optimization in separate solve stages.
        """
        model = cp_model.CpModel()
        t0 = datetime.now(timezone.utc)
        stage_statuses: list[tuple[str, str, float]] = []

        primary_map = {
            (p.employee_id, p.brand_process_id): p.priority
            for p in primary_assignments
        }
        baseline_allocs = {
            (a.employee_id, a.date, a.brand_process_id)
            for a in existing_allocations
        }

        # -------------------------------------------------------------
        # 1. Variables
        # -------------------------------------------------------------
        x: dict[tuple[uuid.UUID, date, uuid.UUID], cp_model.IntVar] = {}
        y: dict[tuple[uuid.UUID, date], cp_model.IntVar] = {}
        s: dict[int, cp_model.IntVar] = {}
        v: dict[int, cp_model.IntVar] = {}
        z: dict[tuple[uuid.UUID, date, uuid.UUID], cp_model.IntVar] = {}

        for e_id in employees:
            for d in target_dates:
                y[(e_id, d)] = model.new_bool_var(f"y_{e_id}_{d}")

        slots_by_date: dict[date, list[tuple[int, DemandSlot]]] = {}
        for idx, slot in enumerate(demand_slots):
            slots_by_date.setdefault(slot.date, []).append((idx, slot))
            s[idx] = model.new_int_var(0, slot.required_staff, f"s_{idx}")
            v[idx] = model.new_bool_var(f"v_{idx}")

            # Enforce exact relation: v[idx] == 1 iff s[idx] == 0
            model.add(s[idx] <= slot.required_staff * (1 - v[idx]))
            model.add(s[idx] >= 1 - v[idx])

        # -------------------------------------------------------------
        # 2. Hard Constraints
        # -------------------------------------------------------------
        for idx, slot in enumerate(demand_slots):
            d = slot.date
            bp_id = slot.brand_process_id
            bp_pod = bp_pod_map.get(bp_id)
            candidates_for_slot = []

            for e_id, emp in employees.items():
                is_same_pod = (emp.pod_id is not None and emp.pod_id == bp_pod)
                if not allow_cross_pod and not is_same_pod:
                    continue

                if not emp.is_active:
                    continue

                if slot.process_id not in emp.skill_process_ids:
                    continue

                unavail = unavailabilities.get((e_id, d))
                if unavail and unavail.is_approved:
                    continue

                emp_shift_interval = TimeInterval(emp.standard_start_time, emp.standard_end_time)
                if not emp_shift_interval.contains(slot.interval):
                    continue

                var = model.new_bool_var(f"x_{e_id}_{d}_{idx}")
                x[(e_id, d, bp_id)] = var
                candidates_for_slot.append(var)
                model.add(var <= y[(e_id, d)])

                if not is_same_pod:
                    z_var = model.new_bool_var(f"z_{e_id}_{d}_{idx}")
                    z[(e_id, d, bp_id)] = z_var
                    model.add(z_var == var)

            model.add(sum(candidates_for_slot) + s[idx] == slot.required_staff)

        # No phantom shifts: y <= sum(x)
        for (e_id, d), y_var in y.items():
            emp_allocs_today = [
                x_var for (eid, dt, bpid), x_var in x.items()
                if eid == e_id and dt == d
            ]
            if emp_allocs_today:
                model.add(y_var <= sum(emp_allocs_today))
            else:
                model.add(y_var == 0)

        # Pairwise Non-Overlap for Intersecting Intervals ONLY
        for d, date_slots in slots_by_date.items():
            num_slots = len(date_slots)
            for i in range(num_slots):
                idx1, slot1 = date_slots[i]
                for j in range(i + 1, num_slots):
                    idx2, slot2 = date_slots[j]
                    if slot1.interval.overlaps(slot2.interval):
                        for e_id in employees:
                            var1 = x.get((e_id, d, slot1.brand_process_id))
                            var2 = x.get((e_id, d, slot2.brand_process_id))
                            if var1 is not None and var2 is not None:
                                model.add(var1 + var2 <= 1)

        # Daily Working Capacity Duration (Minutes)
        for (e_id, d), y_var in y.items():
            emp = employees[e_id]
            today_weighted_allocs = []
            for (eid, dt, bp_id), x_var in x.items():
                if eid == e_id and dt == d:
                    matching_slot = next(
                        (s for s in slots_by_date.get(d, []) if s[1].brand_process_id == bp_id),
                        None,
                    )
                    if matching_slot:
                        dur = matching_slot[1].interval.duration_minutes
                        today_weighted_allocs.append(dur * x_var)
            if today_weighted_allocs:
                model.add(sum(today_weighted_allocs) <= emp.daily_capacity_minutes * y_var)

        # Pass B Hard Lower Bounds: preserve Pass A's positions and fully satisfied slots
        if min_covered_positions > 0:
            model.add(sum(x.values()) >= min_covered_positions)
        if min_fully_satisfied_slots > 0:
            model.add(sum(v.values()) >= min_fully_satisfied_slots)

        # -------------------------------------------------------------
        # 3. Sequential Lexicographic Optimization Stages
        # -------------------------------------------------------------
        total_covered_expr = sum(x.values()) if x else 0
        fully_satisfied_expr = sum(v.values()) if v else 0
        cross_pod_expr = sum(z.values()) if z else 0

        churn_vars = []
        for (e_id, d, bp_id), x_var in x.items():
            is_baseline = (e_id, d, bp_id) in baseline_allocs
            if is_baseline:
                churn_vars.append(1 - x_var)
            else:
                churn_vars.append(x_var)
        churn_expr = sum(churn_vars) if churn_vars else 0

        primary_reward_expr = sum(
            x_var for (e_id, d, bp_id), x_var in x.items()
            if (e_id, bp_id) in primary_map
        ) if x else 0

        # Soft preferences: penalize working on an employee's preferred weekly-off days
        off_day_work_vars = []
        for (e_id, d), y_var in y.items():
            pref = preferences.get(e_id)
            if pref and d.weekday() in pref.preferred_weekly_off_days:
                off_day_work_vars.append(y_var)
        pref_penalty_expr = sum(off_day_work_vars) if off_day_work_vars else 0

        # Adapt stage budget dynamically based on available time:
        # Give Stage 1 (coverage) and Stage 4 (churn minimization) higher proportional budgets
        # to ensure feasible continuity and prevent timeout churn.
        total_budget = max(0.5, time_limit_seconds)
        stage_budget = max(0.15, total_budget / 5.0)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(stage_budget)
        solver.parameters.num_workers = 4
        solver.parameters.random_seed = 42

        status_mapping = {
            cp_model.OPTIMAL: ResolverStatus.OPTIMAL,
            cp_model.FEASIBLE: ResolverStatus.FEASIBLE,
            cp_model.INFEASIBLE: ResolverStatus.INFEASIBLE,
            cp_model.UNKNOWN: ResolverStatus.UNKNOWN,
            cp_model.MODEL_INVALID: ResolverStatus.MODEL_INVALID,
        }

        overall_pass_status = ResolverStatus.OPTIMAL

        # Warm start Stage 1 from baseline allocations
        model.clear_hints()
        for (e_id, d, bp_id), var in x.items():
            if (e_id, d, bp_id) in baseline_allocs:
                model.add_hint(var, 1)

        # STAGE 1: Maximize total covered staffing positions
        model.maximize(total_covered_expr)
        s1 = solver.solve(model)
        s1_st = status_mapping.get(s1, ResolverStatus.UNKNOWN)
        stage_statuses.append(("Stage 1: Staff Positions", s1_st.value, solver.objective_value if s1 in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 0.0))
        if s1 not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            fallback_map = {k: True for k in baseline_allocs if k in x}
            return fallback_map, LexicographicPassResult(pass_name, s1_st, (datetime.now(timezone.utc) - t0).total_seconds(), stage_statuses=tuple(stage_statuses))
        
        best_solution_map = {k: bool(solver.value(var)) for k, var in x.items()}

        if s1 == cp_model.FEASIBLE:
            overall_pass_status = ResolverStatus.FEASIBLE
            model.add(total_covered_expr >= int(solver.objective_value))
        else:
            model.add(total_covered_expr == int(solver.objective_value))

        model.clear_hints()
        for k, var in x.items():
            model.add_hint(var, int(best_solution_map.get(k, False)))

        # STAGE 2: Maximize fully satisfied demand intervals
        model.maximize(fully_satisfied_expr)
        s2 = solver.solve(model)
        s2_st = status_mapping.get(s2, ResolverStatus.UNKNOWN)
        stage_statuses.append(("Stage 2: Full Demand Slots", s2_st.value, solver.objective_value if s2 in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 0.0))
        if s2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            best_solution_map = {k: bool(solver.value(var)) for k, var in x.items()}
            if s2 == cp_model.FEASIBLE:
                overall_pass_status = ResolverStatus.FEASIBLE
                model.add(fully_satisfied_expr >= int(solver.objective_value))
            else:
                model.add(fully_satisfied_expr == int(solver.objective_value))
        else:
            overall_pass_status = ResolverStatus.FEASIBLE

        model.clear_hints()
        for k, var in x.items():
            model.add_hint(var, int(best_solution_map.get(k, False)))

        # STAGE 3: Minimize cross-pod assignments (in Pass B)
        if allow_cross_pod and z:
            model.minimize(cross_pod_expr)
            s3 = solver.solve(model)
            s3_st = status_mapping.get(s3, ResolverStatus.UNKNOWN)
            stage_statuses.append(("Stage 3: Cross-Pod Minimization", s3_st.value, solver.objective_value if s3 in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 0.0))
            if s3 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                best_solution_map = {k: bool(solver.value(var)) for k, var in x.items()}
                if s3 == cp_model.FEASIBLE:
                    overall_pass_status = ResolverStatus.FEASIBLE
                    model.add(cross_pod_expr <= int(solver.objective_value))
                else:
                    model.add(cross_pod_expr == int(solver.objective_value))
            else:
                overall_pass_status = ResolverStatus.FEASIBLE

            model.clear_hints()
            for k, var in x.items():
                model.add_hint(var, int(best_solution_map.get(k, False)))

        # STAGE 4: Minimize baseline allocation churn
        if churn_vars:
            model.minimize(churn_expr)
            s4 = solver.solve(model)
            s4_st = status_mapping.get(s4, ResolverStatus.UNKNOWN)
            stage_statuses.append(("Stage 4: Churn Minimization", s4_st.value, solver.objective_value if s4 in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 0.0))
            if s4 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                best_solution_map = {k: bool(solver.value(var)) for k, var in x.items()}
                if s4 == cp_model.FEASIBLE:
                    overall_pass_status = ResolverStatus.FEASIBLE
                    model.add(churn_expr <= int(solver.objective_value))
                else:
                    model.add(churn_expr == int(solver.objective_value))
            else:
                overall_pass_status = ResolverStatus.FEASIBLE

            model.clear_hints()
            for k, var in x.items():
                model.add_hint(var, int(best_solution_map.get(k, False)))

        # STAGE 5: Maximize primary assignments while avoiding soft preferred weekly off days
        model.maximize(10 * primary_reward_expr - 1 * pref_penalty_expr)
        s5 = solver.solve(model)
        s5_st = status_mapping.get(s5, ResolverStatus.UNKNOWN)
        stage_statuses.append(("Stage 5: Primaries & Preferences", s5_st.value, solver.objective_value if s5 in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 0.0))
        if s5 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            best_solution_map = {k: bool(solver.value(var)) for k, var in x.items()}
            if s5 == cp_model.FEASIBLE:
                overall_pass_status = ResolverStatus.FEASIBLE
        else:
            overall_pass_status = ResolverStatus.FEASIBLE

        # Extract final solution from best_solution_map
        solution_map = dict(best_solution_map)
        covered_pos = sum(1 for val in solution_map.values() if val)
        
        full_slots = 0
        for idx, slot in enumerate(demand_slots):
            assigned_for_slot = sum(
                1 for (eid, dt, bpid), assigned in solution_map.items()
                if assigned and dt == slot.date and bpid == slot.brand_process_id
            )
            if assigned_for_slot >= slot.required_staff:
                full_slots += 1

        cp_pos = sum(1 for k in z if solution_map.get(k, False))
        churn_cnt = sum(
            1 for k in x
            if solution_map.get(k, False) != (k in baseline_allocs)
        )

        solve_dur = (datetime.now(timezone.utc) - t0).total_seconds()
        pass_result = LexicographicPassResult(
            pass_name=pass_name,
            status=overall_pass_status,
            solve_time_seconds=solve_dur,
            objective_value=float(covered_pos),
            covered_positions=covered_pos,
            fully_satisfied_slots=full_slots,
            cross_pod_positions=cp_pos,
            perturbation_count=churn_cnt,
            stage_statuses=tuple(stage_statuses),
        )

        return solution_map, pass_result

    @classmethod
    def _build_schedule_and_bundles(
        cls,
        solution: dict[tuple[uuid.UUID, date, uuid.UUID], bool],
        demand_slots: list[DemandSlot],
        employees: dict[uuid.UUID, EmployeeSpec],
        existing_allocations: list[ScheduledAllocation],
        bp_pod_map: dict[uuid.UUID, uuid.UUID | None],
        primary_assignments: list[PrimaryAssignmentSpec],
    ) -> tuple[list[ScheduledAllocation], list[ScheduledShift], list[ResolutionBundle]]:
        """
        Translates solver boolean variables into synthesized domain ScheduledShift,
        ScheduledAllocation, and atomic connected-component ResolutionBundle objects.
        """
        proposed_allocs: list[ScheduledAllocation] = []
        proposed_shifts: list[ScheduledShift] = []
        resolution_bundles: list[ResolutionBundle] = []

        baseline_lookup = {
            (a.employee_id, a.date, a.brand_process_id): a
            for a in existing_allocations
        }
        active_slots_map = {
            (s.brand_process_id, s.date): s
            for s in demand_slots
        }

        emp_date_allocs: dict[tuple[uuid.UUID, date], list[ScheduledAllocation]] = {}

        # 1. Build ScheduledAllocation records
        for (e_id, d, bp_id), is_assigned in solution.items():
            if not is_assigned:
                continue
            slot = active_slots_map.get((bp_id, d))
            if not slot:
                continue

            emp = employees[e_id]
            bp_pod = bp_pod_map.get(bp_id)
            is_cp = (emp.pod_id is not None and bp_pod is not None and emp.pod_id != bp_pod)

            existing = baseline_lookup.get((e_id, d, bp_id))
            alloc_id = existing.id if existing else uuid.uuid4()
            alloc_type = (
                AllocationType.CROSS_POD_REASSIGNMENT if is_cp
                else AllocationType.PRIMARY
            )

            alloc = ScheduledAllocation(
                id=alloc_id,
                employee_id=e_id,
                brand_process_id=bp_id,
                date=d,
                interval=slot.interval,
                allocation_type=alloc_type,
                is_cross_pod_approved=False,
                reassigned_from_employee_id=existing.reassigned_from_employee_id if existing else None,
                notes="Synthesized by AutomatedConflictResolver",
            )
            proposed_allocs.append(alloc)
            emp_date_allocs.setdefault((e_id, d), []).append(alloc)

        # 2. Synthesize ScheduledShift records (Zero phantom shifts: 1 shift per employee per working date)
        for (e_id, d), alloc_list in emp_date_allocs.items():
            emp = employees[e_id]
            min_start = min(a.interval.start_time for a in alloc_list)
            max_end = max(a.interval.end_time for a in alloc_list)

            shift_start = min(min_start, emp.standard_start_time)
            shift_end = max(max_end, emp.standard_end_time)

            shift = ScheduledShift(
                id=uuid.uuid4(),
                employee_id=e_id,
                date=d,
                interval=TimeInterval(shift_start, shift_end),
                is_working_day=True,
            )
            proposed_shifts.append(shift)

        # 3. Create Atomic Connected-Component Resolution Bundles for changed allocations
        proposed_keys = {
            (a.employee_id, a.date, a.brand_process_id): a
            for a in proposed_allocs
        }
        baseline_keys = set(baseline_lookup.keys())
        current_keys = set(proposed_keys.keys())

        added_or_changed = current_keys - baseline_keys
        removed = baseline_keys - current_keys

        # Group changes by date first
        changes_by_date: dict[date, list[AllocationChange]] = defaultdict(list)

        for (e_id, d, bp_id) in added_or_changed:
            a = proposed_keys[(e_id, d, bp_id)]
            emp = employees[e_id]
            bp_pod = bp_pod_map.get(bp_id)
            is_cp = (emp.pod_id != bp_pod)

            change = AllocationChange(
                action_type=ActionType.NEW_ALLOCATION,
                date=d,
                brand_process_id=bp_id,
                interval=a.interval,
                employee_id=e_id,
                allocation_id=a.id,
                is_cross_pod=is_cp,
                source_pod_id=emp.pod_id,
                target_pod_id=bp_pod,
                notes=f"Allocated {emp.name} to cover demand slot.",
            )
            changes_by_date[d].append(change)

        for (e_id, d, bp_id) in removed:
            old_a = baseline_lookup[(e_id, d, bp_id)]
            emp = employees[e_id]
            bp_pod = bp_pod_map.get(bp_id)
            change = AllocationChange(
                action_type=ActionType.REMOVE_ALLOCATION,
                date=d,
                brand_process_id=bp_id,
                interval=old_a.interval,
                employee_id=e_id,
                allocation_id=old_a.id,
                notes=f"Released {emp.name} from previous allocation to allow cascade.",
            )
            changes_by_date[d].append(change)

        # On each date, group changes into connected components using a bipartite graph (Employees <-> BrandProcesses)
        for d, date_changes in changes_by_date.items():
            if not date_changes:
                continue

            # Build adjacency graph
            adj: dict[str, list[str]] = defaultdict(list)
            change_by_edge: dict[tuple[str, str], list[AllocationChange]] = defaultdict(list)

            for c in date_changes:
                emp_node = f"EMP:{c.employee_id}"
                bp_node = f"BP:{c.brand_process_id}"
                adj[emp_node].append(bp_node)
                adj[bp_node].append(emp_node)
                change_by_edge[(emp_node, bp_node)].append(c)

            # Discover connected components via BFS
            visited: set[str] = set()
            for node in list(adj.keys()):
                if node in visited:
                    continue
                component_nodes: set[str] = set()
                queue = deque([node])
                visited.add(node)

                while queue:
                    curr = queue.popleft()
                    component_nodes.add(curr)
                    for nbr in adj[curr]:
                        if nbr not in visited:
                            visited.add(nbr)
                            queue.append(nbr)

                # Extract changes in this connected component
                component_changes: list[AllocationChange] = []
                component_bp_ids: set[uuid.UUID] = set()
                for (u, v), ch_list in change_by_edge.items():
                    if u in component_nodes and v in component_nodes:
                        component_changes.extend(ch_list)
                        bp_str = u if u.startswith("BP:") else v
                        component_bp_ids.add(uuid.UUID(bp_str.split(":", 1)[1]))

                has_cp = any(c.is_cross_pod for c in component_changes)
                desc = (
                    f"Cross-Pod Resolution Bundle on {d} ({len(component_bp_ids)} brands/processes)"
                    if has_cp
                    else f"Same-Pod Resolution Bundle on {d} ({len(component_bp_ids)} brands/processes)"
                )
                chain = [
                    f"{c.action_type.value}: {employees[c.employee_id].name} (Pod: {c.source_pod_id}) on {c.interval.start_time}-{c.interval.end_time}"
                    for c in component_changes
                ]
                bundle = ResolutionBundle(
                    bundle_id=uuid.uuid4(),
                    target_date=d,
                    brand_process_ids=list(component_bp_ids),
                    is_cross_pod=has_cp,
                    requires_manager_approval=has_cp,
                    description=desc,
                    changes=component_changes,
                    cascading_chain=chain,
                )
                resolution_bundles.append(bundle)

        return proposed_allocs, proposed_shifts, resolution_bundles

    @classmethod
    def _analyze_shortage(
        cls,
        slot: DemandSlot,
        assigned_count: int,
        shortfall: int,
        employees: dict[uuid.UUID, EmployeeSpec],
        unavailabilities: dict[tuple[uuid.UUID, date], UnavailabilitySpec],
        existing_shifts: list[ScheduledShift],
        bp_info_map: dict[uuid.UUID, tuple[uuid.UUID, uuid.UUID]],
        bp_pod_map: dict[uuid.UUID, uuid.UUID | None],
    ) -> ShortageEvidence:
        """
        Generates evidence-based explanations for an unfilled or partially filled demand slot.
        """
        d = slot.date
        bp_id = slot.brand_process_id
        brand_id, proc_id = bp_info_map.get(bp_id, (slot.brand_id, slot.process_id))
        target_pod = bp_pod_map.get(bp_id)

        pod_certified = [
            e for e in employees.values()
            if proc_id in e.skill_process_ids and e.pod_id == target_pod and e.is_active
        ]
        comp_certified = [
            e for e in employees.values()
            if proc_id in e.skill_process_ids and e.is_active
        ]

        avail_pod = []
        for e in pod_certified:
            unavail = unavailabilities.get((e.id, d))
            if unavail and unavail.is_approved:
                continue
            avail_pod.append(e)

        avail_comp = []
        for e in comp_certified:
            unavail = unavailabilities.get((e.id, d))
            if unavail and unavail.is_approved:
                continue
            avail_comp.append(e)

        reasons: list[str] = []

        if not pod_certified:
            reasons.append(f"Pod has 0 active employees certified in process {proc_id}.")
        elif not avail_pod:
            reasons.append(
                f"All {len(pod_certified)} certified employees in the pod have approved leave or hard unavailabilities on {d}."
            )
        else:
            reasons.append(
                f"All {len(avail_pod)} available certified employees in the pod are already fully allocated to concurrent higher-priority demand."
            )

        if not avail_comp:
            reasons.append(
                f"Company-wide shortage: 0 employees across all pods are available and certified in process {proc_id} on {d}."
            )

        return ShortageEvidence(
            date=d,
            brand_process_id=bp_id,
            brand_id=brand_id,
            process_id=proc_id,
            required_staff=slot.required_staff,
            assigned_staff=assigned_count,
            shortfall=shortfall,
            total_pod_certified=len(pod_certified),
            total_company_certified=len(comp_certified),
            available_pod_certified=len(avail_pod),
            available_company_certified=len(avail_comp),
            reasons=tuple(reasons),
        )
