import {
  User,
  Pod,
  Employee,
  ProcessItem,
  Brand,
  BrandProcess,
  PrimaryAssignment,
  EmployeeUnavailability,
  RosterSummary,
  RosterGridView,
  BackupCandidate,
  AllocationLogItem,
  BrandOperatingSchedule,
  WorkforceAnalytics,
  ResolverPreviewResponse,
  ResolverApplyRequest,
  ResolverApplyResponse,
} from './types';

const BASE_URL = '/api/v1';

function getCsrfToken(): string {
  const match = document.cookie.match(new RegExp('(^| )csrf_token=([^;]+)'));
  return match ? match[2] : '';
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');

  const csrf = getCsrfToken();
  if (csrf) {
    headers.set('X-CSRF-Token', csrf);
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    let errorDetail = 'An error occurred';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      errorDetail = await response.text();
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    request<User>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  getCurrentUser: () => request<User>('/auth/me'),
  logout: () => request<{ message: string }>('/auth/logout', { method: 'POST' }),

  // Workforce
  getPods: () => request<Pod[]>('/pods'),
  createPod: (name: string) =>
    request<Pod>('/pods', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),

  getEmployees: () => request<Employee[]>('/employees'),
  createEmployee: (data: Partial<Employee>) =>
    request<Employee>('/employees', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Availability & Leaves
  getEmployeeUnavailability: (employeeId: string) =>
    request<EmployeeUnavailability[]>(`/employees/${employeeId}/unavailability`),
  addEmployeeUnavailability: (
    employeeId: string,
    data: { date: string; reason_type: string; is_approved: boolean; notes?: string }
  ) =>
    request<EmployeeUnavailability>(`/employees/${employeeId}/unavailability`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  deleteEmployeeUnavailability: (employeeId: string, unavailabilityId: string) =>
    request<void>(`/employees/${employeeId}/unavailability/${unavailabilityId}`, {
      method: 'DELETE',
    }),

  // Preferences
  getEmployeePreferences: (employeeId: string) =>
    request<{ id: string; employee_id: string; preferred_weekly_off_days: string; notes?: string } | null>(
      `/employees/${employeeId}/preferences`
    ),
  setEmployeePreferences: (employeeId: string, preferred_weekly_off_days: string, notes?: string) =>
    request<{ id: string; employee_id: string; preferred_weekly_off_days: string; notes?: string }>(
      `/employees/${employeeId}/preferences`,
      {
        method: 'PUT',
        body: JSON.stringify({ preferred_weekly_off_days, notes }),
      }
    ),

  // Operations
  getBrands: () => request<Brand[]>('/brands'),
  getBrandOperatingSchedule: (brandId: string) =>
    request<BrandOperatingSchedule>(`/brands/${brandId}/operating-schedule`),
  createBrand: (code: string, name: string) =>
    request<Brand>('/brands', {
      method: 'POST',
      body: JSON.stringify({ code, name }),
    }),

  getProcesses: () => request<ProcessItem[]>('/processes'),
  createProcess: (code: string, name: string, description?: string) =>
    request<ProcessItem>('/processes', {
      method: 'POST',
      body: JSON.stringify({ code, name, description }),
    }),

  getBrandProcesses: () => request<BrandProcess[]>('/brand-processes'),
  createBrandProcess: (brand_id: string, process_id: string) =>
    request<BrandProcess>('/brand-processes', {
      method: 'POST',
      body: JSON.stringify({ brand_id, process_id }),
    }),

  getAssignments: () => request<PrimaryAssignment[]>('/assignments'),
  createAssignment: (data: { employee_id: string; brand_process_id: string; effective_from: string; priority: number }) =>
    request<PrimaryAssignment>('/assignments', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Roster
  getRosters: () => request<RosterSummary[]>('/rosters'),
  generateRoster: (name: string, month: number, year: number) =>
    request<RosterSummary>('/rosters/generate', {
      method: 'POST',
      body: JSON.stringify({ name, month, year }),
    }),
  getRosterGrid: (roster_id: string, view_type: string, filter_id?: string) => {
    let url = `/rosters/${roster_id}/grid?view_type=${view_type}`;
    if (filter_id) url += `&filter_id=${filter_id}`;
    return request<RosterGridView>(url);
  },
  publishRoster: (roster_id: string) =>
    request<RosterSummary>(`/rosters/${roster_id}/publish`, { method: 'POST' }),
  createChildVersion: (roster_id: string) =>
    request<RosterSummary>(`/rosters/${roster_id}/create-child-version`, { method: 'POST' }),

  // Reassignment
  getBackupCandidates: (roster_id: string, brand_process_id: string, date: string, start_time: string, end_time: string) =>
    request<BackupCandidate[]>(
      `/rosters/${roster_id}/backup-candidates?brand_process_id=${brand_process_id}&target_date=${date}&start_time=${start_time}&end_time=${end_time}`
    ),
  previewReassignment: (data: {
    roster_id: string;
    date: string;
    brand_process_id: string;
    start_time: string;
    end_time: string;
    target_employee_id: string;
    source_employee_id?: string | null;
  }) =>
    request<{
      is_eligible: boolean;
      rejection_reason?: string | null;
      allocation_type: string;
      requires_ops_manager_approval: boolean;
      affected_conflicts_count: number;
    }>(`/rosters/${data.roster_id}/reassign/preview`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  applyReassignment: (data: {
    roster_id: string;
    date: string;
    brand_process_id: string;
    start_time: string;
    end_time: string;
    target_employee_id: string;
    source_employee_id?: string | null;
    reason?: string | null;
    confirm_cross_pod_approval: boolean;
  }) =>
    request<{ status: string; allocation_id: string; resolved_conflicts: number }>(
      `/rosters/${data.roster_id}/reassign/apply`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    ),
  getAllocationLog: (roster_id: string, dynamicOnly: boolean = false) =>
    request<AllocationLogItem[]>(
      `/rosters/${roster_id}/allocation-log?dynamic_only=${dynamicOnly}`
    ),
  getRosterAnalytics: (roster_id: string) =>
    request<WorkforceAnalytics>(`/rosters/${roster_id}/analytics`),
  previewConflictResolutions: (roster_id: string) =>
    request<ResolverPreviewResponse>(`/rosters/${roster_id}/resolver/preview`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  applyConflictResolutions: (data: ResolverApplyRequest) =>
    request<ResolverApplyResponse>(`/rosters/${data.roster_id}/resolver/apply`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  // Brand Portal
  getBrandProfile: () => request<import('./types').BrandProfile>('/brand-portal/me'),
  submitBrandRequest: (data: {
    brand_process_id?: string;
    operating_mode: string;
    custom_days_of_week?: string[];
    operating_start_time: string;
    operating_end_time: string;
    min_headcount: number;
    effective_from_date?: string;
    effective_to_date?: string;
    notes?: string;
  }) =>
    request<import('./types').BrandChangeRequest>('/brand-portal/requests', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getBrandRequests: () => request<import('./types').BrandChangeRequest[]>('/brand-portal/requests'),
  getBrandRequestDetail: (requestId: string) =>
    request<import('./types').BrandChangeRequest>(`/brand-portal/requests/${requestId}`),
  previewBrandRequestImpact: (requestId: string, rosterId?: string) => {
    let url = `/brand-portal/requests/${requestId}/preview-impact`;
    if (rosterId) url += `?roster_id=${rosterId}`;
    return request<import('./types').BrandImpactPreview>(url, { method: 'POST' });
  },
  approveBrandRequest: (requestId: string, managerNotes?: string) =>
    request<import('./types').BrandChangeRequest>(`/brand-portal/requests/${requestId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ manager_notes: managerNotes }),
    }),
  rejectBrandRequest: (requestId: string, managerNotes: string) =>
    request<import('./types').BrandChangeRequest>(`/brand-portal/requests/${requestId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ manager_notes: managerNotes }),
    }),
  markBrandRequestImplemented: (requestId: string) =>
    request<import('./types').BrandChangeRequest>(`/brand-portal/requests/${requestId}/mark-implemented`, {
      method: 'POST',
    }),
};
