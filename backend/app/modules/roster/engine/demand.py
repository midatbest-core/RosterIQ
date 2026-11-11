from __future__ import annotations

from datetime import date, time
import uuid

from app.modules.roster.engine.domain import (
    DemandSlot,
    HolidayBehavior,
    OperatingOverrideSpec,
    OperatingPatternSpec,
    TimeInterval,
)


class DemandResolver:
    """
    Deterministic demand resolution engine.
    
    Precedence Hierarchy:
    1. Date-specific override:
       - If is_closed == True => demand = 0 (CLOSED)
       - If is_closed == False => use override staffing and interval (or pattern interval if none provided)
    2. Recurring weekday rule:
       - Check if target date's weekday is in operating_days.
       - If NOT in operating_days => demand = 0 (CLOSED).
       - If in operating_days => determine baseline staffing (min_staffing_weekend if Sat/Sun, else min_staffing_weekday).
    3. Holiday behaviour (ONLY if date is in company_holidays AND weekday is operating):
       - If holiday_behavior == CLOSED => demand = 0 (CLOSED)
       - If holiday_behavior == NORMAL => retains applicable regular staffing
       - If holiday_behavior == REDUCED => demand = min_staffing_holiday (retains normal operating hours)
    """

    @staticmethod
    def resolve_slot(
        brand_process_id: uuid.UUID,
        brand_id: uuid.UUID,
        process_id: uuid.UUID,
        target_date: date,
        pattern: OperatingPatternSpec,
        override: OperatingOverrideSpec | None,
        is_company_holiday: bool,
    ) -> DemandSlot:
        weekday = target_date.weekday()  # 0=Monday ... 6=Sunday
        is_weekend = weekday in (5, 6)

        # ---------------------------------------------------------
        # Level 1: Date-Specific Override
        # ---------------------------------------------------------
        if override is not None:
            if override.is_closed:
                return DemandSlot(
                    brand_process_id=brand_process_id,
                    brand_id=brand_id,
                    process_id=process_id,
                    date=target_date,
                    interval=TimeInterval(pattern.start_time, pattern.end_time),
                    required_staff=0,
                    is_operating=False,
                    resolution_source="DATE_OVERRIDE_CLOSED",
                )
            
            # Open with override parameters
            start = override.override_start_time or pattern.start_time
            end = override.override_end_time or pattern.end_time
            default_staff = pattern.min_staffing_weekend if is_weekend else pattern.min_staffing_weekday
            staff = override.override_min_staffing if override.override_min_staffing is not None else default_staff
            return DemandSlot(
                brand_process_id=brand_process_id,
                brand_id=brand_id,
                process_id=process_id,
                date=target_date,
                interval=TimeInterval(start, end),
                required_staff=staff,
                is_operating=staff > 0,
                resolution_source="DATE_OVERRIDE_OPEN",
            )

        # ---------------------------------------------------------
        # Level 2: Recurring Weekday Rule
        # ---------------------------------------------------------
        if weekday not in pattern.operating_days:
            # Recurring rule says this weekday is NOT an operating day for this brand-process
            return DemandSlot(
                brand_process_id=brand_process_id,
                brand_id=brand_id,
                process_id=process_id,
                date=target_date,
                interval=TimeInterval(pattern.start_time, pattern.end_time),
                required_staff=0,
                is_operating=False,
                resolution_source="WEEKDAY_NON_OPERATING",
            )

        # Baseline staffing for an operating weekday/weekend
        baseline_staff = pattern.min_staffing_weekend if is_weekend else pattern.min_staffing_weekday

        # ---------------------------------------------------------
        # Level 3: Holiday Behaviour (applies when date is a company holiday)
        # ---------------------------------------------------------
        if is_company_holiday:
            if pattern.holiday_behavior == HolidayBehavior.CLOSED:
                return DemandSlot(
                    brand_process_id=brand_process_id,
                    brand_id=brand_id,
                    process_id=process_id,
                    date=target_date,
                    interval=TimeInterval(pattern.start_time, pattern.end_time),
                    required_staff=0,
                    is_operating=False,
                    resolution_source="HOLIDAY_BEHAVIOR_CLOSED",
                )
            elif pattern.holiday_behavior == HolidayBehavior.REDUCED:
                return DemandSlot(
                    brand_process_id=brand_process_id,
                    brand_id=brand_id,
                    process_id=process_id,
                    date=target_date,
                    interval=TimeInterval(pattern.start_time, pattern.end_time),
                    required_staff=pattern.min_staffing_holiday,
                    is_operating=pattern.min_staffing_holiday > 0,
                    resolution_source="HOLIDAY_BEHAVIOR_REDUCED",
                )
            else:  # NORMAL
                return DemandSlot(
                    brand_process_id=brand_process_id,
                    brand_id=brand_id,
                    process_id=process_id,
                    date=target_date,
                    interval=TimeInterval(pattern.start_time, pattern.end_time),
                    required_staff=baseline_staff,
                    is_operating=baseline_staff > 0,
                    resolution_source="HOLIDAY_BEHAVIOR_NORMAL",
                )

        # Normal recurring operating day (not a holiday)
        return DemandSlot(
            brand_process_id=brand_process_id,
            brand_id=brand_id,
            process_id=process_id,
            date=target_date,
            interval=TimeInterval(pattern.start_time, pattern.end_time),
            required_staff=baseline_staff,
            is_operating=baseline_staff > 0,
            resolution_source="WEEKDAY_OPERATING_RULE",
        )

