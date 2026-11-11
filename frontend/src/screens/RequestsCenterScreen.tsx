import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  BrandChangeRequest,
  EmployeeAvailabilityRequest,
  BrandImpactPreview,
  EmployeeImpactPreview,
  RosterSummary,
} from '../services/types';
import {
  FileText,
  Building2,
  User,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  Eye,
  ChevronRight,
  ShieldAlert,
  ArrowRight,
  Check,
  X,
  Calendar,
  Sparkles,
} from 'lucide-react';

interface RequestsCenterScreenProps {
  rosters: RosterSummary[];
  selectedRosterId: string;
  onRefreshRosters: () => Promise<void>;
  onNavigateToConflicts?: () => void;
}

export const RequestsCenterScreen: React.FC<RequestsCenterScreenProps> = ({
  rosters,
  selectedRosterId,
  onRefreshRosters,
  onNavigateToConflicts,
}) => {
  const [activeTab, setActiveTab] = useState<'brand' | 'employee'>('brand');
  const [brandRequests, setBrandRequests] = useState<BrandChangeRequest[]>([]);
  const [employeeRequests, setEmployeeRequests] = useState<EmployeeAvailabilityRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Review & Impact Modal State
  const [selectedBrandReq, setSelectedBrandReq] = useState<BrandChangeRequest | null>(null);
  const [brandPreview, setBrandPreview] = useState<BrandImpactPreview | null>(null);
  const [selectedEmpReq, setSelectedEmpReq] = useState<EmployeeAvailabilityRequest | null>(null);
  const [empPreview, setEmpPreview] = useState<EmployeeImpactPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Action form
  const [managerNotes, setManagerNotes] = useState('');
  const [rejectModalOpen, setRejectModalOpen] = useState(false);

  useEffect(() => {
    loadRequests();
  }, []);

  const loadRequests = async () => {
    try {
      setLoading(true);
      setError(null);
      const [bReqs, eReqs] = await Promise.all([
        api.getBrandRequests(),
        api.getEmployeeRequests(),
      ]);
      setBrandRequests(bReqs);
      setEmployeeRequests(eReqs);
    } catch (err: any) {
      setError(err.message || 'Failed to load requests');
    } finally {
      setLoading(false);
    }
  };

  const handleInspectBrand = async (req: BrandChangeRequest) => {
    setSelectedBrandReq(req);
    setSelectedEmpReq(null);
    setManagerNotes('');
    try {
      setPreviewLoading(true);
      const preview = await api.previewBrandRequestImpact(req.id, selectedRosterId || undefined);
      setBrandPreview(preview);
    } catch (err: any) {
      console.error(err);
      setBrandPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleInspectEmployee = async (req: EmployeeAvailabilityRequest) => {
    setSelectedEmpReq(req);
    setSelectedBrandReq(null);
    setManagerNotes('');
    try {
      setPreviewLoading(true);
      const preview = await api.previewEmployeeRequestImpact(req.id);
      setEmpPreview(preview);
    } catch (err: any) {
      console.error(err);
      setEmpPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleApproveBrand = async () => {
    if (!selectedBrandReq) return;
    try {
      setActionLoading(true);
      setError(null);
      await api.approveBrandRequest(selectedBrandReq.id, managerNotes || undefined);
      setSuccess(`Brand operating plan change approved. Affected draft rosters marked STALE.`);
      setSelectedBrandReq(null);
      setBrandPreview(null);
      await onRefreshRosters();
      await loadRequests();
    } catch (err: any) {
      setError(err.message || 'Failed to approve brand request');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectBrand = async () => {
    if (!selectedBrandReq || !managerNotes.trim()) return;
    try {
      setActionLoading(true);
      setError(null);
      await api.rejectBrandRequest(selectedBrandReq.id, managerNotes);
      setSuccess(`Brand request rejected with feedback sent to partner.`);
      setSelectedBrandReq(null);
      setBrandPreview(null);
      setRejectModalOpen(false);
      await loadRequests();
    } catch (err: any) {
      setError(err.message || 'Failed to reject brand request');
    } finally {
      setActionLoading(false);
    }
  };

  const handleApproveEmployee = async () => {
    if (!selectedEmpReq) return;
    try {
      setActionLoading(true);
      setError(null);
      await api.approveEmployeeRequest(selectedEmpReq.id, managerNotes || undefined);
      setSuccess(`Employee leave request approved. Conflicting shifts ready for automated conflict resolution.`);
      setSelectedEmpReq(null);
      setEmpPreview(null);
      await onRefreshRosters();
      await loadRequests();
    } catch (err: any) {
      setError(err.message || 'Failed to approve employee leave request');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectEmployee = async () => {
    if (!selectedEmpReq || !managerNotes.trim()) return;
    try {
      setActionLoading(true);
      setError(null);
      await api.rejectEmployeeRequest(selectedEmpReq.id, managerNotes);
      setSuccess(`Employee leave request rejected with review notes.`);
      setSelectedEmpReq(null);
      setEmpPreview(null);
      setRejectModalOpen(false);
      await loadRequests();
    } catch (err: any) {
      setError(err.message || 'Failed to reject employee request');
    } finally {
      setActionLoading(false);
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
            Under Review
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
            <CheckCircle2 className="w-3 h-3" /> Implemented
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

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <FileText className="w-6 h-6 text-indigo-400" /> Requests & Change Approval Centre
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Review partner brand operating plan changes and employee absence requests with instant impact simulation
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onNavigateToConflicts && (
            <button
              onClick={onNavigateToConflicts}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-indigo-300 text-xs font-medium border border-slate-700"
            >
              <ShieldAlert className="w-4 h-4 text-rose-400" /> Open Conflict Resolver
            </button>
          )}
          <button
            onClick={loadRequests}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Alerts */}
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

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveTab('brand')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeTab === 'brand'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          }`}
        >
          <Building2 className="w-4 h-4" /> Brand Plan Changes ({brandRequests.length})
        </button>
        <button
          onClick={() => setActiveTab('employee')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeTab === 'employee'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          }`}
        >
          <User className="w-4 h-4" /> Employee Leaves & Absences ({employeeRequests.length})
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
        </div>
      ) : activeTab === 'brand' ? (
        brandRequests.length === 0 ? (
          <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 space-y-2">
            <Building2 className="w-10 h-10 text-slate-600 mx-auto" />
            <p className="text-sm font-medium">No brand plan change requests pending.</p>
            <p className="text-xs text-slate-500">
              When partner brands submit operating day or hours adjustments, they will appear here.
            </p>
          </div>
        ) : (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/60 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Submitted</th>
                    <th className="px-4 py-3">Brand</th>
                    <th className="px-4 py-3">Process</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Requested Plan</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {brandRequests.map((req) => (
                    <tr key={req.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-400">
                        {new Date(req.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 font-semibold text-white text-xs">{req.brand_name || 'Brand'}</td>
                      <td className="px-4 py-3 text-xs text-slate-300">{req.process_name || 'All Processes'}</td>
                      <td className="px-4 py-3 text-xs">
                        <span className="font-mono text-indigo-300">{req.request_type}</span>
                      </td>
                      <td className="px-4 py-3 text-xs max-w-xs truncate text-slate-300 font-mono">
                        {req.requested_configuration}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">{getStatusBadge(req.status)}</td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <button
                          onClick={() => handleInspectBrand(req)}
                          className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium inline-flex items-center gap-1 shadow-sm"
                        >
                          Review & Preview <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )
      ) : employeeRequests.length === 0 ? (
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 space-y-2">
          <User className="w-10 h-10 text-slate-600 mx-auto" />
          <p className="text-sm font-medium">No employee absence requests recorded.</p>
          <p className="text-xs text-slate-500">
            When staff members submit leave requests, they will appear here for review.
          </p>
        </div>
      ) : (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Submitted</th>
                  <th className="px-4 py-3">Employee</th>
                  <th className="px-4 py-3">Dates</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Notes</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {employeeRequests.map((req) => (
                  <tr key={req.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-400">
                      {new Date(req.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 font-semibold text-white text-xs">
                      {req.employee_name || 'Employee'}
                    </td>
                    <td className="px-4 py-3 font-medium text-white text-xs whitespace-nowrap">
                      {req.start_date} {req.start_date !== req.end_date ? `to ${req.end_date}` : ''}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      <span className="font-mono text-indigo-300">{req.reason_type}</span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400 max-w-xs truncate">
                      {req.notes || <span className="text-slate-600 italic">None</span>}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">{getStatusBadge(req.status)}</td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <button
                        onClick={() => handleInspectEmployee(req)}
                        className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium inline-flex items-center gap-1 shadow-sm"
                      >
                        Review & Impact <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Brand Review Modal */}
      {selectedBrandReq && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-indigo-400" /> Review Brand Plan Change: {selectedBrandReq.brand_name}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Request #{selectedBrandReq.id.slice(0, 8)} • Type: {selectedBrandReq.request_type}
                </p>
              </div>
              <button
                onClick={() => {
                  setSelectedBrandReq(null);
                  setBrandPreview(null);
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
            ) : brandPreview ? (
              <div className="space-y-4 text-xs">
                {/* Summary Box */}
                <div className="p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-200">
                  <p className="font-semibold text-sm mb-1">
                    {brandPreview.invalid_existing_allocations_count > 0 || brandPreview.new_uncovered_intervals_count > 0
                      ? '⚠️ Workforce Staffing Adjustments Required'
                      : '✓ Seamless Adaptation'}
                  </p>
                  <p className="text-slate-300">{brandPreview.summary}</p>
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block">Affected Days</span>
                    <span className="text-base font-bold text-white">{brandPreview.affected_dates.length}</span>
                  </div>
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block">Invalid Allocations</span>
                    <span className="text-base font-bold text-amber-300">
                      {brandPreview.invalid_existing_allocations_count}
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block">Affected Staff</span>
                    <span className="text-base font-bold text-indigo-300">
                      {brandPreview.affected_employees_count}
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block">New Uncovered</span>
                    <span className="text-base font-bold text-rose-400">
                      {brandPreview.new_uncovered_intervals_count}
                    </span>
                  </div>
                </div>

                {/* Notes Input */}
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Operations Manager Notes / Response
                  </label>
                  <textarea
                    rows={2}
                    value={managerNotes}
                    onChange={(e) => setManagerNotes(e.target.value)}
                    placeholder="Enter review feedback or approval notes..."
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            ) : (
              <div className="text-center py-6 text-slate-500">
                Unable to simulate preview (no active draft roster found).
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => {
                  setSelectedBrandReq(null);
                  setBrandPreview(null);
                }}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
              >
                Close
              </button>

              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={actionLoading || selectedBrandReq.status !== 'PENDING'}
                  onClick={handleRejectBrand}
                  className="px-4 py-2 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 text-xs font-medium disabled:opacity-50"
                >
                  Reject Request
                </button>
                <button
                  type="button"
                  disabled={actionLoading || selectedBrandReq.status !== 'PENDING'}
                  onClick={handleApproveBrand}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 disabled:opacity-50 flex items-center gap-1.5"
                >
                  <Check className="w-4 h-4" /> Approve Plan Change
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Employee Review Modal */}
      {selectedEmpReq && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <User className="w-5 h-5 text-indigo-400" /> Review Leave: {selectedEmpReq.employee_name}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  {selectedEmpReq.start_date} to {selectedEmpReq.end_date} • {selectedEmpReq.reason_type}
                </p>
              </div>
              <button
                onClick={() => {
                  setSelectedEmpReq(null);
                  setEmpPreview(null);
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
            ) : empPreview ? (
              <div className="space-y-4 text-xs">
                {/* Conflict Status */}
                <div
                  className={`p-3.5 rounded-xl border ${
                    empPreview.conflicting_allocations_count > 0
                      ? 'bg-rose-500/10 border-rose-500/30 text-rose-200'
                      : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
                  }`}
                >
                  <p className="font-semibold text-sm mb-1">
                    {empPreview.conflicting_allocations_count > 0
                      ? `⚠️ ${empPreview.conflicting_allocations_count} Conflicting Shifts Detected`
                      : '✓ No Shift Conflicts'}
                  </p>
                  <p className="text-slate-300">{empPreview.summary}</p>
                </div>

                {/* Conflicting Shifts List */}
                {empPreview.conflicting_allocations.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-semibold text-white">Conflicting Shifts to Reassign:</h4>
                    <div className="space-y-1.5 max-h-40 overflow-y-auto">
                      {empPreview.conflicting_allocations.map((c) => (
                        <div
                          key={c.allocation_id}
                          className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 flex items-center justify-between text-xs"
                        >
                          <div>
                            <span className="font-semibold text-white">{c.date}</span> ({c.time})
                            <p className="text-[11px] text-slate-400">
                              {c.brand} • {c.process}
                            </p>
                          </div>
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                            Unavailability Conflict
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Notes Input */}
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Manager Review Feedback
                  </label>
                  <textarea
                    rows={2}
                    value={managerNotes}
                    onChange={(e) => setManagerNotes(e.target.value)}
                    placeholder="Enter review notes for employee..."
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            ) : null}

            {/* Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => {
                  setSelectedEmpReq(null);
                  setEmpPreview(null);
                }}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
              >
                Close
              </button>

              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={actionLoading || selectedEmpReq.status !== 'PENDING'}
                  onClick={handleRejectEmployee}
                  className="px-4 py-2 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 text-xs font-medium disabled:opacity-50"
                >
                  Reject Request
                </button>
                <button
                  type="button"
                  disabled={actionLoading || selectedEmpReq.status !== 'PENDING'}
                  onClick={handleApproveEmployee}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 disabled:opacity-50 flex items-center gap-1.5"
                >
                  <Check className="w-4 h-4" /> Approve Leave
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default RequestsCenterScreen;
