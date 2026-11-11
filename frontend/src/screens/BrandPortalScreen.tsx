import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { BrandProfile, BrandChangeRequest, BrandImpactPreview } from '../services/types';
import {
  Building2,
  Calendar,
  Clock,
  Users,
  Send,
  AlertCircle,
  CheckCircle2,
  XCircle,
  FileText,
  RefreshCw,
  Plus,
  HelpCircle,
  Activity,
  ChevronRight,
} from 'lucide-react';

export const BrandPortalScreen: React.FC = () => {
  const [profile, setProfile] = useState<BrandProfile | null>(null);
  const [requests, setRequests] = useState<BrandChangeRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Modal form state
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [selectedProcessId, setSelectedProcessId] = useState<string>('');
  const [requestType, setRequestType] = useState<string>('OPERATING_DAYS');
  const [operatingDays, setOperatingDays] = useState<number[]>([0, 1, 2, 3, 4]); // Mon-Fri
  const [startTime, setStartTime] = useState<string>('09:00:00');
  const [endTime, setEndTime] = useState<string>('18:00:00');
  const [minWeekday, setMinWeekday] = useState<number>(1);
  const [minWeekend, setMinWeekend] = useState<number>(0);
  const [holidayBehavior, setHolidayBehavior] = useState<string>('CLOSED');
  const [overrideDate, setOverrideDate] = useState<string>('');
  const [isClosed, setIsClosed] = useState<boolean>(false);
  const [reason, setReason] = useState<string>('');

  // Selected request for impact preview
  const [selectedRequest, setSelectedRequest] = useState<BrandChangeRequest | null>(null);
  const [impactPreview, setImpactPreview] = useState<BrandImpactPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [profData, reqsData] = await Promise.all([
        api.getBrandProfile(),
        api.getBrandRequests(),
      ]);
      setProfile(profData);
      setRequests(reqsData);
      if (profData.processes && profData.processes.length > 0 && !selectedProcessId) {
        setSelectedProcessId(profData.processes[0].brand_process_id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load brand portal data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setError(null);

      const payload: any = {
        brand_process_id: selectedProcessId || undefined,
        request_type: requestType,
        reason: reason,
      };

      if (requestType === 'OPERATING_DAYS') {
        payload.operating_days = operatingDays;
      } else if (requestType === 'OPERATING_HOURS') {
        payload.start_time = startTime.length === 5 ? `${startTime}:00` : startTime;
        payload.end_time = endTime.length === 5 ? `${endTime}:00` : endTime;
      } else if (requestType === 'MIN_STAFFING') {
        payload.min_staffing_weekday = Number(minWeekday);
        payload.min_staffing_weekend = Number(minWeekend);
      } else if (requestType === 'HOLIDAY_BEHAVIOR') {
        payload.holiday_behavior = holidayBehavior;
      } else if (requestType === 'DATE_OVERRIDE') {
        payload.override_date = overrideDate;
        payload.is_closed = isClosed;
        if (!isClosed) {
          payload.start_time = startTime.length === 5 ? `${startTime}:00` : startTime;
          payload.end_time = endTime.length === 5 ? `${endTime}:00` : endTime;
          payload.min_staffing_weekday = Number(minWeekday);
        }
      }

      await (api as any).submitBrandRequest(payload);
      setSuccess('Operating plan change request submitted successfully to Operations Managers.');
      setShowRequestModal(false);
      setReason('');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to submit request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleInspectRequest = async (req: BrandChangeRequest) => {
    setSelectedRequest(req);
    try {
      setPreviewLoading(true);
      const preview = await api.previewBrandRequestImpact(req.id);
      setImpactPreview(preview);
    } catch (err: any) {
      console.error('Impact preview error:', err);
      setImpactPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  const toggleDay = (idx: number) => {
    if (operatingDays.includes(idx)) {
      setOperatingDays(operatingDays.filter((d) => d !== idx));
    } else {
      setOperatingDays([...operatingDays, idx].sort());
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
            <Clock className="w-3 h-3" /> Pending Review
          </span>
        );
      case 'UNDER_REVIEW':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300">
            <Activity className="w-3 h-3" /> Under Review
          </span>
        );
      case 'APPROVED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
            <CheckCircle2 className="w-3 h-3" /> Approved
          </span>
        );
      case 'ROSTER_PENDING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300">
            <RefreshCw className="w-3 h-3 animate-spin" /> Roster Re-sync Pending
          </span>
        );
      case 'IMPLEMENTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-100 text-teal-800 dark:bg-teal-950/60 dark:text-teal-300">
            <CheckCircle2 className="w-3 h-3" /> Published & Implemented
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300">
            <XCircle className="w-3 h-3" /> Rejected
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300">
            {status}
          </span>
        );
    }
  };

  if (loading && !profile) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
          <p className="text-sm text-slate-500">Loading brand portal...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Brand Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-gradient-to-r from-indigo-900/40 via-purple-900/30 to-slate-900/40 p-6 rounded-2xl border border-indigo-500/20 backdrop-blur-xl">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold text-2xl shadow-inner">
            <Building2 className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-white tracking-tight">{profile?.name}</h1>
              <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">
                {profile?.code}
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Timezone: <span className="text-slate-200 font-medium">{profile?.timezone}</span> • Partner Brand Self-Service Portal
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowRequestModal(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium shadow-lg shadow-indigo-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          <Plus className="w-4 h-4" /> Request Plan Change
        </button>
      </div>

      {/* Notifications / Alerts */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-300">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-400" />
          <div className="flex-1 text-sm">{error}</div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200">
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      )}

      {success && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-3 text-emerald-300">
          <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5 text-emerald-400" />
          <div className="flex-1 text-sm">{success}</div>
          <button onClick={() => setSuccess(null)} className="text-emerald-400 hover:text-emerald-200">
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Active Operating Patterns Overview */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Calendar className="w-5 h-5 text-indigo-400" /> Current Operating Plan & Processes
          </h2>
          <span className="text-xs text-slate-400">
            Changes require Operations Manager approval and roster re-sync
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {profile?.processes.map((proc) => {
            const activeDays = proc.operating_days || [];
            return (
              <div
                key={proc.brand_process_id}
                className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all space-y-4 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-white text-base">{proc.process_name}</h3>
                    <p className="text-xs text-slate-400">Holiday: {proc.holiday_behavior}</p>
                  </div>
                  <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-slate-800 text-indigo-300 border border-slate-700">
                    {activeDays.length === 7 ? '365 Days' : activeDays.length === 6 ? 'Mon–Sat' : activeDays.length === 5 ? 'Mon–Fri' : 'Custom'}
                  </span>
                </div>

                <div className="space-y-2 text-xs text-slate-300">
                  <div className="flex items-center justify-between py-1 border-b border-slate-800/80">
                    <span className="text-slate-400 flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-slate-500" /> Operating Window:
                    </span>
                    <span className="font-medium text-slate-200">
                      {proc.start_time.slice(0, 5)} - {proc.end_time.slice(0, 5)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-slate-800/80">
                    <span className="text-slate-400 flex items-center gap-1.5">
                      <Users className="w-3.5 h-3.5 text-slate-500" /> Staffing:
                    </span>
                    <span className="font-medium text-indigo-300">
                      {proc.min_staffing_weekday} wkday / {proc.min_staffing_weekend} wkend
                    </span>
                  </div>

                  <div className="py-1">
                    <span className="text-slate-400 block mb-1">Active Days:</span>
                    <div className="flex flex-wrap gap-1">
                      {dayLabels.map((dayAbbr, idx) => {
                        const isActive = activeDays.includes(idx);
                        return (
                          <span
                            key={dayAbbr}
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                              isActive
                                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
                                : 'bg-slate-800 text-slate-500 border border-slate-800/80'
                            }`}
                          >
                            {dayAbbr}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Change Requests Section */}
      <div className="space-y-4 pt-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-400" /> Change Request History
          </h2>
          <button
            onClick={loadData}
            className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>

        {requests.length === 0 ? (
          <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-400 space-y-2">
            <FileText className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-sm font-medium">No plan change requests submitted yet.</p>
            <p className="text-xs text-slate-500">
              Submit a request whenever you need to adjust operating days, hours, or minimum staffing requirements.
            </p>
          </div>
        ) : (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/60 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Submitted</th>
                    <th className="px-4 py-3">Process</th>
                    <th className="px-4 py-3">Request Type</th>
                    <th className="px-4 py-3">Requested Plan</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Manager Notes</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {requests.map((req) => (
                    <tr key={req.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-400">
                        {new Date(req.created_at).toLocaleDateString()} {new Date(req.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="px-4 py-3 font-medium text-white text-xs">
                        {req.process_name || 'All Brand Processes'}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        <span className="font-mono text-indigo-300">{req.request_type}</span>
                      </td>
                      <td className="px-4 py-3 text-xs max-w-xs truncate text-slate-300">
                        {req.requested_configuration}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {getStatusBadge(req.status)}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400 max-w-xs truncate">
                        {req.review_notes || <span className="text-slate-600 italic">None yet</span>}
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <button
                          onClick={() => handleInspectRequest(req)}
                          className="px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700 inline-flex items-center gap-1"
                        >
                          Impact Preview <ChevronRight className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Impact Preview Modal */}
      {selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Activity className="w-5 h-5 text-indigo-400" /> Plan Change Impact Preview
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Request #{selectedRequest.id.slice(0, 8)} • Status: {selectedRequest.status}
                </p>
              </div>
              <button
                onClick={() => {
                  setSelectedRequest(null);
                  setImpactPreview(null);
                }}
                className="text-slate-400 hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {previewLoading ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin" />
              </div>
            ) : impactPreview ? (
              <div className="space-y-4 text-xs">
                {/* Status Callout */}
                <div className="p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-200">
                  <p className="font-semibold text-sm mb-1">
                    {impactPreview.invalid_existing_allocations_count > 0 || impactPreview.new_uncovered_intervals_count > 0
                      ? '⚠️ Staffing Adjustments Required'
                      : '✓ Seamless Adaptation'}
                  </p>
                  <p className="text-slate-300">
                    {impactPreview.summary || 'Simulated against active draft roster.'}
                  </p>
                </div>

                {/* Metrics Breakdown */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block">Affected Days</span>
                    <span className="text-base font-bold text-white">{impactPreview.affected_dates.length} days</span>
                  </div>
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block">Invalid Allocations</span>
                    <span className="text-base font-bold text-amber-300">
                      {impactPreview.invalid_existing_allocations_count}
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block">Affected Staff</span>
                    <span className="text-base font-bold text-indigo-300">
                      {impactPreview.affected_employees_count}
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block">New Uncovered</span>
                    <span className="text-base font-bold text-rose-400">
                      {impactPreview.new_uncovered_intervals_count}
                    </span>
                  </div>
                </div>

                {/* Impacted Employees */}
                {impactPreview.affected_employees && impactPreview.affected_employees.length > 0 && (
                  <div className="space-y-1.5">
                    <h4 className="font-semibold text-white">Affected Personnel:</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {impactPreview.affected_employees.map((emp) => (
                        <span
                          key={emp.id}
                          className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700"
                        >
                          {emp.name} {emp.date ? `(${emp.date})` : ''}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500">
                Unable to simulate preview (no active draft roster found).
              </div>
            )}

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => {
                  setSelectedRequest(null);
                  setImpactPreview(null);
                }}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Request Modal */}
      {showRequestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Send className="w-5 h-5 text-indigo-400" /> Request Operating Plan Change
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Propose adjustments to working days, hours, or minimum staffing
                </p>
              </div>
              <button
                onClick={() => setShowRequestModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmitRequest} className="space-y-4 text-xs">
              {/* Process Select */}
              <div>
                <label className="block text-slate-300 font-medium mb-1">Target Process</label>
                <select
                  value={selectedProcessId}
                  onChange={(e) => setSelectedProcessId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">All Processes for {profile?.name}</option>
                  {profile?.processes.map((proc) => (
                    <option key={proc.brand_process_id} value={proc.brand_process_id}>
                      {proc.process_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Request Type */}
              <div>
                <label className="block text-slate-300 font-medium mb-1">Change Type</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { type: 'OPERATING_DAYS', label: 'Working Days (e.g. 365, Mon-Sat)' },
                    { type: 'OPERATING_HOURS', label: 'Operating Window Hours' },
                    { type: 'MIN_STAFFING', label: 'Minimum Staffing Headcount' },
                    { type: 'HOLIDAY_BEHAVIOR', label: 'Holiday Behavior' },
                    { type: 'DATE_OVERRIDE', label: 'Specific Date Override' },
                  ].map((item) => (
                    <button
                      key={item.type}
                      type="button"
                      onClick={() => setRequestType(item.type)}
                      className={`p-2.5 rounded-xl border text-left font-medium transition-all ${
                        requestType === item.type
                          ? 'bg-indigo-600/20 border-indigo-500 text-indigo-200'
                          : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Conditional Form Fields */}
              {requestType === 'OPERATING_DAYS' && (
                <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                  <span className="block text-slate-300 font-medium">Select Active Operating Days:</span>
                  <div className="flex flex-wrap gap-2">
                    {dayLabels.map((day, idx) => {
                      const selected = operatingDays.includes(idx);
                      return (
                        <button
                          key={day}
                          type="button"
                          onClick={() => toggleDay(idx)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                            selected
                              ? 'bg-indigo-600 text-white border-indigo-500'
                              : 'bg-slate-900 text-slate-400 border-slate-700 hover:border-slate-600'
                          }`}
                        >
                          {day}
                        </button>
                      );
                    })}
                  </div>
                  <div className="flex gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setOperatingDays([0, 1, 2, 3, 4])}
                      className="text-[11px] text-indigo-400 hover:underline"
                    >
                      Mon–Fri
                    </button>
                    <span className="text-slate-600">•</span>
                    <button
                      type="button"
                      onClick={() => setOperatingDays([0, 1, 2, 3, 4, 5])}
                      className="text-[11px] text-indigo-400 hover:underline"
                    >
                      Mon–Sat
                    </button>
                    <span className="text-slate-600">•</span>
                    <button
                      type="button"
                      onClick={() => setOperatingDays([0, 1, 2, 3, 4, 5, 6])}
                      className="text-[11px] text-indigo-400 hover:underline"
                    >
                      365 Days
                    </button>
                  </div>
                </div>
              )}

              {requestType === 'OPERATING_HOURS' && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Start Time</label>
                    <input
                      type="time"
                      step="1"
                      value={startTime}
                      onChange={(e) => setStartTime(e.target.value)}
                      required
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">End Time</label>
                    <input
                      type="time"
                      step="1"
                      value={endTime}
                      onChange={(e) => setEndTime(e.target.value)}
                      required
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>
              )}

              {requestType === 'MIN_STAFFING' && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Weekday Staffing</label>
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={minWeekday}
                      onChange={(e) => setMinWeekday(Number(e.target.value))}
                      required
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Weekend Staffing</label>
                    <input
                      type="number"
                      min="0"
                      max="20"
                      value={minWeekend}
                      onChange={(e) => setMinWeekend(Number(e.target.value))}
                      required
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>
              )}

              {requestType === 'HOLIDAY_BEHAVIOR' && (
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Holiday Operation</label>
                  <select
                    value={holidayBehavior}
                    onChange={(e) => setHolidayBehavior(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="CLOSED">CLOSED (No staff required on public holidays)</option>
                    <option value="NORMAL">NORMAL (Regular operating hours & staffing)</option>
                    <option value="REDUCED">REDUCED (Minimal staffing)</option>
                  </select>
                </div>
              )}

              {requestType === 'DATE_OVERRIDE' && (
                <div className="space-y-3 p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Override Date</label>
                    <input
                      type="date"
                      value={overrideDate}
                      onChange={(e) => setOverrideDate(e.target.value)}
                      required
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isClosed}
                      onChange={(e) => setIsClosed(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-0"
                    />
                    <span>Completely Closed on this Date</span>
                  </label>
                </div>
              )}

              {/* Justification Reason */}
              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Business Justification (Required)
                </label>
                <textarea
                  rows={3}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  required
                  placeholder="e.g., Seasonal campaign ramp-up requiring weekend operations"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500 placeholder-slate-600"
                />
              </div>

              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 flex items-start gap-2">
                <HelpCircle className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                <span>
                  Submitting this request will not alter live operations immediately. An Operations Manager will review the impact, resolve any workforce conflicts, and publish the updated roster.
                </span>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRequestModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || reason.length < 3}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium flex items-center gap-2 shadow-lg shadow-indigo-600/30"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" /> Submitting...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" /> Submit to Ops Manager
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default BrandPortalScreen;
