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
  AppNotification,
} from './types';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const BASE_URL = `${API_BASE}/api/v1`;

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
  login: async (email: string, password: string): Promise<User> => {
    const res = await request<{ user: User; csrf_token: string } | User>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    return (res as any).user ? (res as any).user : (res as User);
  },
  getCurrentUser: () => request<User>('/auth/me'),
  logout: () => request<{ message: string }>('/auth/logout', { method: 'POST' }),
  getNotifications: () => request<AppNotification[]>('/auth/notifications'),
  markNotificationRead: (id: string) =>
    request<{ status: string }>(`/auth/notifications/${id}/read`, { method: 'POST' }),
  deleteNotification: (id: string) =>
    request<{ status: string; id: string }>(`/auth/notifications/${id}`, { method: 'DELETE' }),

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
  // Employee Portal
  getEmployeeProfile: () => request<import('./types').EmployeeProfile>('/employee-portal/me'),
  getEmployeeTasks: (month?: number, year?: number) => {
    let url = '/employee-portal/tasks';
    const params: string[] = [];
    if (month) params.push(`month=${month}`);
    if (year) params.push(`year=${year}`);
    if (params.length > 0) url += `?${params.join('&')}`;
    return request<import('./types').EmployeeTaskItem[]>(url);
  },
  getPodAllocations: (month?: number, year?: number) => {
    let url = '/employee-portal/pod-allocations';
    const params: string[] = [];
    if (month) params.push(`month=${month}`);
    if (year) params.push(`year=${year}`);
    if (params.length > 0) url += `?${params.join('&')}`;
    return request<import('./types').EmployeeTaskItem[]>(url);
  },
  submitEmployeeRequest: (data: {
    employee_id?: string;
    request_type: string;
    start_date: string;
    end_date: string;
    reason_type: string;
    notes: string;
    details?: string;
  }) =>
    request<import('./types').EmployeeAvailabilityRequest>('/employee-portal/requests', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getEmployeeRequests: () =>
    request<import('./types').EmployeeAvailabilityRequest[]>('/employee-portal/requests'),
  getEmployeeRequestDetail: (requestId: string) =>
    request<import('./types').EmployeeAvailabilityRequest>(`/employee-portal/requests/${requestId}`),
  previewEmployeeRequestImpact: (requestId: string, rosterId?: string) => {
    let url = `/employee-portal/requests/${requestId}/preview-impact`;
    if (rosterId) url += `?roster_id=${rosterId}`;
    return request<import('./types').EmployeeImpactPreview>(url, { method: 'POST' });
  },
  approveEmployeeRequest: (requestId: string, managerNotes?: string, rosterId?: string) => {
    let url = `/employee-portal/requests/${requestId}/approve`;
    if (rosterId) url += `?roster_id=${rosterId}`;
    return request<import('./types').EmployeeAvailabilityRequest>(url, {
      method: 'POST',
      body: JSON.stringify({ manager_notes: managerNotes }),
    });
  },
  rejectEmployeeRequest: (requestId: string, managerNotes: string) =>
    request<import('./types').EmployeeAvailabilityRequest>(`/employee-portal/requests/${requestId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ manager_notes: managerNotes }),
    }),
  markEmployeeRequestImplemented: (requestId: string, rosterId?: string) => {
    let url = `/employee-portal/requests/${requestId}/mark-implemented`;
    if (rosterId) url += `?roster_id=${rosterId}`;
    return request<import('./types').EmployeeAvailabilityRequest>(url, { method: 'POST' });
  },

  exportRosterCsv: async (rosterId: string, viewType: string = 'company', filterId?: string): Promise<void> => {
    const params = new URLSearchParams();
    if (viewType) params.append('view_type', viewType);
    if (filterId) params.append('filter_id', filterId);
    const url = `${BASE_URL}/rosters/${rosterId}/export/csv?${params.toString()}`;
    const response = await fetch(url, {
      method: 'GET',
      credentials: 'include',
    });
    if (!response.ok) {
      let errorDetail = 'Export failed';
      try {
        const errJson = await response.json();
        errorDetail = errJson.detail || errJson.message || errorDetail;
      } catch {
        errorDetail = await response.text();
      }
      throw new Error(errorDetail);
    }
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition');
    let filename = `roster_${viewType}.csv`;
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1];
    }
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },

  exportBrandScheduleCsv: async (rosterId?: string): Promise<void> => {
    const url = rosterId ? `${BASE_URL}/brand-portal/export/csv?roster_id=${rosterId}` : `${BASE_URL}/brand-portal/export/csv`;
    const response = await fetch(url, { method: 'GET', credentials: 'include' });
    if (!response.ok) {
      let errorDetail = 'Export failed';
      try {
        const errJson = await response.json();
        errorDetail = errJson.detail || errJson.message || errorDetail;
      } catch {
        errorDetail = await response.text();
      }
      throw new Error(errorDetail);
    }
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition');
    let filename = 'brand_schedule.csv';
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1];
    }
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },

  exportEmployeeScheduleCsv: async (rosterId?: string): Promise<void> => {
    const url = rosterId ? `${BASE_URL}/employee-portal/export/csv?roster_id=${rosterId}` : `${BASE_URL}/employee-portal/export/csv`;
    const response = await fetch(url, { method: 'GET', credentials: 'include' });
    if (!response.ok) {
      let errorDetail = 'Export failed';
      try {
        const errJson = await response.json();
        errorDetail = errJson.detail || errJson.message || errorDetail;
      } catch {
        errorDetail = await response.text();
      }
      throw new Error(errorDetail);
    }
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition');
    let filename = 'my_schedule.csv';
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1];
    }
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },

  getGoogleSheetsStatus: async (): Promise<{
    enabled: boolean;
    client_id_configured: boolean;
    service_account_configured: boolean;
    message: string;
    scopes: string[];
  }> => {
    return request('/rosters/export/google-sheets/status');
  },

  exportRosterGoogleSheets: async (
    rosterId: string,
    viewType: string = 'company',
    filterId?: string,
    googleAccessToken?: string
  ): Promise<{
    spreadsheet_id: string;
    spreadsheet_url: string;
    title: string;
    rows_exported: number;
  }> => {
    return request(`/rosters/${rosterId}/export/google-sheets`, {
      method: 'POST',
      body: JSON.stringify({
        view_type: viewType,
        filter_id: filterId || null,
        google_access_token: googleAccessToken || null,
      }),
    });
  },

  exportBrandGoogleSheets: async (
    rosterId?: string,
    googleAccessToken?: string
  ): Promise<{
    spreadsheet_id: string;
    spreadsheet_url: string;
    title: string;
    rows_exported: number;
  }> => {
    return request('/brand-portal/export/google-sheets', {
      method: 'POST',
      body: JSON.stringify({
        roster_id: rosterId || null,
        google_access_token: googleAccessToken || null,
      }),
    });
  },

  exportEmployeeGoogleSheets: async (
    rosterId?: string,
    googleAccessToken?: string
  ): Promise<{
    spreadsheet_id: string;
    spreadsheet_url: string;
    title: string;
    rows_exported: number;
  }> => {
    return request('/employee-portal/export/google-sheets', {
      method: 'POST',
      body: JSON.stringify({
        roster_id: rosterId || null,
        google_access_token: googleAccessToken || null,
      }),
    });
  },
};
