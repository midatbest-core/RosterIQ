import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  EmployeeProfile,
  EmployeeTaskItem,
  EmployeeAvailabilityRequest,
} from '../services/types';
import {
  User as UserIcon,
  Calendar,
  Clock,
  Briefcase,
  CheckCircle2,
  XCircle,
  AlertCircle,
  FileText,
  RefreshCw,
  Plus,
  Send,
  HelpCircle,
  Activity,
  Layers,
  ChevronRight,
} from 'lucide-react';

export const EmployeePortalScreen: React.FC = () => {
  const [profile, setProfile] = useState<EmployeeProfile | null>(null);
  const [tasks, setTasks] = useState<EmployeeTaskItem[]>([]);
  const [requests, setRequests] = useState<EmployeeAvailabilityRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Month / Year filter for checklist
  const [selectedMonth, setSelectedMonth] = useState<number>(11);
  const [selectedYear, setSelectedYear] = useState<number>(2026);

  // Leave Request Modal state
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [requestType, setRequestType] = useState<string>('LEAVE');
  const [reasonType, setReasonType] = useState<string>('PLANNED_LEAVE');
  const [startDate, setStartDate] = useState<string>('2026-11-15');
  const [endDate, setEndDate] = useState<string>('2026-11-15');
  const [notes, setNotes] = useState<string>('');

  useEffect(() => {
    loadData();
  }, [selectedMonth, selectedYear]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [profData, tasksData, reqsData] = await Promise.all([
        api.getEmployeeProfile(),
        api.getEmployeeTasks(selectedMonth, selectedYear),
        api.getEmployeeRequests(),
      ]);
      setProfile(profData);
      setTasks(tasksData);
      setRequests(reqsData);
    } catch (err: any) {
      setError(err.message || 'Failed to load employee portal data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setError(null);
      await api.submitEmployeeRequest({
        request_type: requestType,
        reason_type: reasonType,
        start_date: startDate,
        end_date: endDate,
        notes: notes,
      });

      setSuccess('Leave / Availability adjustment request submitted to Operations Managers.');
      setShowRequestModal(false);
      setNotes('');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to submit request');
    } finally {
      setSubmitting(false);
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
          <p className="text-sm text-slate-500">Loading employee workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header Profile Card */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 p-6 rounded-2xl border border-slate-800 backdrop-blur-xl shadow-lg">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold text-xl shadow-inner">
            <UserIcon className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-white tracking-tight">{profile?.name}</h1>
              <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">
                {profile?.employee_code}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-2 flex-wrap">
              <span>Pod: <strong className="text-slate-200">{profile?.pod_name || 'Unassigned'}</strong></span>
              <span>•</span>
              <span>Pod Lead: <strong className="text-slate-200">{profile?.pod_lead_name || 'N/A'}</strong></span>
              <span>•</span>
              <span>Shift: <strong className="text-indigo-300">{profile?.standard_start_time.slice(0, 5)} - {profile?.standard_end_time.slice(0, 5)}</strong> ({Math.round((profile?.daily_capacity_minutes || 0) / 60)}h)</span>
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowRequestModal(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium shadow-lg shadow-indigo-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          <Plus className="w-4 h-4" /> Request Leave / Absence
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

      {/* Two Column Layout: Primary Assignments & Skills */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Primary Brand / Process Assignments */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <Briefcase className="w-4 h-4 text-indigo-400" /> Primary Dedicated Assignments
          </h2>
          {profile?.primary_assignments.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No dedicated primary assignments recorded.</p>
          ) : (
            <div className="space-y-2">
              {profile?.primary_assignments.map((pa) => (
                <div
                  key={pa.assignment_id}
                  className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs"
                >
                  <div>
                    <p className="font-semibold text-white">{pa.brand_name}</p>
                    <p className="text-[11px] text-slate-400">{pa.process_name}</p>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    Primary Core
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Process Qualifications / Skills */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-purple-400" /> Certified Skills & Backup Qualifications
          </h2>
          {profile?.skills.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No skills registered.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {profile?.skills.map((s) => (
                <div
                  key={s.process_id}
                  className="px-3 py-1.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center gap-2 text-xs"
                >
                  <span className="text-white font-medium">{s.process_name}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    {s.proficiency}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Task Checklist for the Employee */}
      <div className="space-y-4 pt-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Calendar className="w-5 h-5 text-indigo-400" /> My Shift & Task Checklist
            </h2>
            <p className="text-xs text-slate-400">
              Allocated work shifts across active published & draft operational rosters
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(Number(e.target.value))}
              className="bg-slate-900 border border-slate-700 text-white rounded-lg px-2.5 py-1.5"
            >
              {[
                { m: 10, label: 'October 2026' },
                { m: 11, label: 'November 2026' },
                { m: 12, label: 'December 2026' },
              ].map((item) => (
                <option key={item.m} value={item.m}>
                  {item.label}
                </option>
              ))}
            </select>
            <button
              onClick={loadData}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {tasks.length === 0 ? (
          <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-400 space-y-2">
            <Calendar className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-sm font-medium">No shifts scheduled for this period.</p>
            <p className="text-xs text-slate-500">
              When a roster is generated or published, your assigned shifts and brand tasks will appear here.
            </p>
          </div>
        ) : (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/60 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Day</th>
                    <th className="px-4 py-3">Brand & Process</th>
                    <th className="px-4 py-3">Shift Window</th>
                    <th className="px-4 py-3">Allocation Role</th>
                    <th className="px-4 py-3">Roster State</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {tasks.map((task) => (
                    <tr key={task.allocation_id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap text-xs font-mono font-medium text-white">
                        {task.date}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400">{task.day_of_week}</td>
                      <td className="px-4 py-3 text-xs">
                        <strong className="text-white block">{task.brand_name}</strong>
                        <span className="text-[11px] text-slate-400">{task.process_name}</span>
                      </td>
                      <td className="px-4 py-3 text-xs whitespace-nowrap">
                        <span className="flex items-center gap-1.5 text-indigo-300">
                          <Clock className="w-3.5 h-3.5 text-indigo-400" />
                          {task.start_time.slice(0, 5)} - {task.end_time.slice(0, 5)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            task.allocation_type === 'PRIMARY'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : task.allocation_type === 'SAME_POD_REASSIGNMENT'
                              ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                              : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          }`}
                        >
                          {task.allocation_type.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                          {task.roster_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Requests History */}
      <div className="space-y-4 pt-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <FileText className="w-5 h-5 text-indigo-400" /> Leave & Absence Request History
        </h2>

        {requests.length === 0 ? (
          <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-400 space-y-2">
            <FileText className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-sm font-medium">No leave requests submitted yet.</p>
            <p className="text-xs text-slate-500">
              Submit an absence request whenever you need time off, sick leave, or weekly off rescheduling.
            </p>
          </div>
        ) : (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/60 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Submitted</th>
                    <th className="px-4 py-3">Dates</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Reason / Notes</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Manager Feedback</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {requests.map((req) => (
                    <tr key={req.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-400">
                        {new Date(req.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 font-medium text-white text-xs whitespace-nowrap">
                        {req.start_date} {req.start_date !== req.end_date ? `to ${req.end_date}` : ''}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        <span className="font-mono text-indigo-300">{req.reason_type}</span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-300 max-w-xs truncate">
                        {req.notes || <span className="text-slate-600 italic">None</span>}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {getStatusBadge(req.status)}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400 max-w-xs truncate">
                        {req.review_notes || <span className="text-slate-600 italic">Pending manager review</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Leave Request Modal */}
      {showRequestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Send className="w-5 h-5 text-indigo-400" /> Request Leave or Availability Change
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Send absence request to Operations Manager for review and conflict resolution
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
              <div>
                <label className="block text-slate-300 font-medium mb-1">Absence Category</label>
                <select
                  value={reasonType}
                  onChange={(e) => setReasonType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="PLANNED_LEAVE">PLANNED_LEAVE (Annual / Personal Time Off)</option>
                  <option value="SICK_LEAVE">SICK_LEAVE (Medical / Unplanned Leave)</option>
                  <option value="APPROVED_OFF">APPROVED_OFF (Weekly Off Swap / Adjustment)</option>
                  <option value="COMP_OFF">COMP_OFF (Compensatory Off)</option>
                  <option value="TRAINING">TRAINING (Professional Development)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Reason / Notes (Required)</label>
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  required
                  placeholder="e.g., Annual family event / doctor appointment"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500 placeholder-slate-600"
                />
              </div>

              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 flex items-start gap-2">
                <HelpCircle className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                <span>
                  Submitting this request will not alter your schedule immediately. The Operations Manager will review the request, reassign any conflicting shifts to eligible qualified backups, and notify you upon resolution.
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
                  disabled={submitting || notes.length < 3}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium flex items-center gap-2 shadow-lg shadow-indigo-600/30"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" /> Submitting...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" /> Send Request
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
export default EmployeePortalScreen;

