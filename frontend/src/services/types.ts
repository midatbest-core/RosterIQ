export interface User {
  id: string;
  email: string;
  role: 'ADMIN' | 'OPERATIONS_MANAGER';
  is_active: boolean;
}

export interface Pod {
  id: string;
  name: string;
  lead_employee_id?: string | null;
  is_active: boolean;
}

export interface Employee {
  id: string;
  employee_code: string;
  name: string;
  email: string;
  pod_id?: string | null;
  status: 'ACTIVE' | 'INACTIVE';
  daily_capacity_minutes: number;
  standard_start_time: string;
  standard_end_time: string;
}

export interface ProcessItem {
  id: string;
  code: string;
  name: string;
  description?: string;
  status: 'ACTIVE' | 'INACTIVE';
}

export interface Brand {
  id: string;
  code: string;
  name: string;
  status: 'ACTIVE' | 'INACTIVE';
}

export interface BrandProcess {
  id: string;
  brand_id: string;
  process_id: string;
  timezone: string;
  holiday_behavior: 'CLOSED' | 'NORMAL' | 'REDUCED';
  holiday_min_employees?: number | null;
  is_active: boolean;
}

export interface OperatingPattern {
  id: string;
  brand_process_id: string;
  operating_days: string;
  start_time: string;
  end_time: string;
  min_staffing_weekday: number;
  min_staffing_weekend: number;
  holiday_behavior: 'CLOSED' | 'NORMAL' | 'REDUCED';
  min_staffing_holiday: number;
}

export interface PrimaryAssignment {
  id: string;
  employee_id: string;
  brand_process_id: string;
  effective_from: string;
  effective_to?: string | null;
  priority: number;
  is_active: boolean;
}

export interface EmployeeUnavailability {
  id: string;
  employee_id: string;
  date: string;
  reason_type: 'PLANNED_LEAVE' | 'SICK_LEAVE' | 'APPROVED_OFF' | 'COMP_OFF' | 'TRAINING';
  is_approved: boolean;
  notes?: string | null;
}

export interface RosterSummary {
  id: string;
  name: string;
  month: number;
  year: number;
  version: number;
  parent_roster_id?: string | null;
  status: 'DRAFT' | 'VALIDATED' | 'PUBLISHED' | 'STALE';
  config_hash?: string | null;
  created_by: string;
  created_at: string;
  published_at?: string | null;
  total_shifts: number;
  total_allocations: number;
  total_conflicts: number;
  hard_violations_count: number;
  soft_warnings_count: number;
}

export interface AllocationCell {
  allocation_id: string;
  brand_process_id: string;
  brand_id: string;
  brand_name: string;
  process_id: string;
  process_name: string;
  employee_id: string;
  employee_name: string;
  start_time: string;
  end_time: string;
  allocation_type: 'PRIMARY' | 'SAME_POD_REASSIGNMENT' | 'CROSS_POD_REASSIGNMENT';
  reassigned_from_employee_id?: string | null;
  is_cross_pod_approved: boolean;
}

export interface DayCell {
  date: string;
  day_of_week: number;
  is_working: boolean;
  shift_start?: string | null;
  shift_end?: string | null;
  allocations: AllocationCell[];
  conflicts: string[];
}

export interface GridRow {
  row_id: string;
  row_type: 'EMPLOYEE' | 'POD' | 'BRAND_PROCESS' | 'PROCESS_BRAND';
  title: string;
  subtitle?: string | null;
  group_id?: string | null;
  group_name?: string | null;
  days: Record<string, DayCell>;
}

export interface RosterGridView {
  roster_id: string;
  month: number;
  year: number;
  version: number;
  status: 'DRAFT' | 'VALIDATED' | 'PUBLISHED' | 'STALE';
  view_type: 'company' | 'pod' | 'brand' | 'process' | 'employee';
  dates: string[];
  rows: GridRow[];
  summary_conflicts: RosterConflict[];
}

export interface RosterConflict {
  id: string;
  date: string;
  brand_process_id?: string | null;
  employee_id?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  severity: 'HARD_VIOLATION' | 'SOFT_WARNING';
  conflict_type: string;
  description: string;
  is_resolved: boolean;
}

export interface BackupCandidate {
  employee_id: string;
  name: string;
  pod_id?: string | null;
  pod_name?: string | null;
  is_same_pod: boolean;
  requires_approval: boolean;
  prefers_off_on_day: boolean;
}

export interface AllocationLogItem {
  id: string;
  roster_id: string;
  date: string;
  start_time: string;
  end_time: string;
  brand_id: string;
  brand_name: string;
  process_id: string;
  process_name: string;
  employee_id: string;
  employee_name: string;
  employee_pod_name?: string | null;
  allocation_type: 'PRIMARY' | 'SAME_POD_REASSIGNMENT' | 'CROSS_POD_REASSIGNMENT';
  reassigned_from_employee_id?: string | null;
  reassigned_from_employee_name?: string | null;
  reassignment_reason?: string | null;
  is_cross_pod_approved: boolean;
  approved_by_user_id?: string | null;
  approved_by_email?: string | null;
  approved_at?: string | null;
  created_at: string;
}

export interface OperatingOverrideItem {
  date: string;
  is_closed: boolean;
  override_start_time?: string | null;
  override_end_time?: string | null;
  override_min_staffing?: number | null;
  reason?: string | null;
}

export interface AssignedEmployeeItem {
  id: string;
  code: string;
  name: string;
  pod_name: string;
  priority: number;
}

export interface BrandProcessScheduleItem {
  brand_process_id: string;
  process_id: string;
  process_name: string;
  process_code: string;
  pattern_label: string;
  operating_days: number[];
  start_time: string;
  end_time: string;
  min_staffing_weekday: number;
  min_staffing_weekend: number;
  holiday_behavior: 'CLOSED' | 'NORMAL' | 'REDUCED';
  min_staffing_holiday: number;
  overrides: OperatingOverrideItem[];
  assigned_employees: AssignedEmployeeItem[];
}

export interface BrandOperatingSchedule {
  brand_id: string;
  brand_name: string;
  brand_code: string;
  status: string;
  processes: BrandProcessScheduleItem[];
}

export interface PodAnalytics {
  pod_id: string;
  pod_name: string;
  lead_name: string;
  employee_count: number;
  available_capacity_hours: number;
  scheduled_hours: number;
  utilization_pct: number;
  status: 'DEFICIT' | 'BALANCED' | 'SURPLUS';
  net_hours_gap: number;
  employees_needed: number;
  free_employees_count: number;
  skills_summary: string[];
}

export interface WorkforceAnalytics {
  roster_id: string;
  month: number;
  year: number;
  status: string;
  total_demand_slots: number;
  total_demand_hours: number;
  scheduled_allocations: number;
  scheduled_hours: number;
  demand_coverage_pct: number;
  total_employees: number;
  total_capacity_hours: number;
  workforce_utilization_pct: number;
  hard_conflicts_count: number;
  pods: PodAnalytics[];
  recommendations: string[];
}

export interface ResolverAllocationChange {
  action_type: string;
  allocation_id: string | null;
  date: string;
  start_time: string;
  end_time: string;
  brand_name: string;
  process_name: string;
  new_employee_id: string | null;
  new_employee_name: string | null;
  new_employee_pod: string | null;
  previous_employee_id: string | null;
  previous_employee_name: string | null;
  is_cross_pod: boolean;
  explanation: string;
}

export interface ResolverBundle {
  bundle_id: string;
  requires_cross_pod_approval: boolean;
  explanation: string;
  affected_dates: string[];
  changes: ResolverAllocationChange[];
  affected_conflicts_count: number;
}

export interface ResolverShortage {
  demand_slot_id: string;
  date: string;
  brand_name: string;
  process_name: string;
  start_time: string;
  end_time: string;
  primary_employee_names: string[];
  root_cause: string;
  explanation: string;
}

export interface ResolverPreviewResponse {
  roster_id: string;
  target_roster_id: string;
  is_published: boolean;
  requires_child_revision: boolean;
  status: string;
  initial_conflicts_count: number;
  resolvable_conflicts_count: number;
  unresolvable_conflicts_count: number;
  coverage_before_pct: number;
  coverage_after_pct: number;
  automatically_resolvable_bundles: ResolverBundle[];
  pending_approval_bundles: ResolverBundle[];
  unresolvable_shortages: ResolverShortage[];
  passes: Array<{ pass_name: string; status: string; solve_time_seconds: number }>;
  validation_passed: boolean;
  validation_conflicts: Array<{ severity: string; conflict_type: string; description: string; date: string }>;
}

export interface ResolverApplyRequest {
  roster_id: string;
  approve_cross_pod: boolean;
  approved_bundle_ids?: string[] | null;
  create_child_if_published?: boolean;
}

export interface ResolverApplyResponse {
  status: string;
  roster_id: string;
  version: number;
  is_new_version: boolean;
  applied_bundles_count: number;
  applied_changes_count: number;
  resolved_conflicts_count: number;
  remaining_conflicts_count: number;
  coverage_pct: number;
  validation_passed: boolean;
  validation_conflicts_count: number;
  applied_at: string;
}




