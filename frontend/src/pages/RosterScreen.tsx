import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  RosterSummary,
  RosterGridView,
  GridRow,
  DayCell,
  RosterConflict,
  BackupCandidate,
} from '../services/types';
import {
  Calendar,
  AlertTriangle,
  CheckCircle,
  Clock,
  UserCheck,
  ChevronRight,
  ShieldAlert,
  ArrowRightLeft,
  Lock,
  GitBranch,
} from 'lucide-react';

export const RosterScreen: React.FC = () => {
  const [rosters, setRosters] = useState<RosterSummary[]>([]);
  const [selectedRosterId, setSelectedRosterId] = useState<string>('');
  const [viewMode, setViewMode] = useState<'company' | 'pod' | 'brand' | 'process' | 'employee'>('company');
  const [gridData, setGridData] = useState<RosterGridView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New Roster Modal state
  const [showGenModal, setShowGenModal] = useState(false);
  const [genName, setGenName] = useState('November 2026 Operations Roster');
  const [genMonth, setGenMonth] = useState(11);
  const [genYear, setGenYear] = useState(2026);

  // Reassignment Modal state
  const [reassignSlot, setReassignSlot] = useState<{
    date: string;
    brand_process_id: string;
    brand_name: string;
    process_name: string;
    start_time: string;
    end_time: string;
    source_employee_id?: string;
  } | null>(null);

  const [candidates, setCandidates] = useState<BackupCandidate[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>('');
  const [confirmCrossPod, setConfirmCrossPod] = useState(false);
  const [reassignReason, setReassignReason] = useState('Absence backup coverage');
  const [reassignSuccessMsg, setReassignSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    loadRosters();
  }, []);

  useEffect(() => {
    if (selectedRosterId) {
      loadGrid(selectedRosterId, viewMode);
    }
  }, [selectedRosterId, viewMode]);

  const loadRosters = async () => {
    try {
      setLoading(true);
      const list = await api.getRosters();
      setRosters(list);
      if (list.length > 0 && !selectedRosterId) {
        setSelectedRosterId(list[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load rosters');
    } finally {
      setLoading(false);
    }
  };

  const loadGrid = async (rosterId: string, mode: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getRosterGrid(rosterId, mode);
      setGridData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load grid data');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const newRoster = await api.generateRoster(genName, genMonth, genYear);
      setShowGenModal(false);
      await loadRosters();
      setSelectedRosterId(newRoster.id);
    } catch (err: any) {
      setError(err.message || 'Generation failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!selectedRosterId) return;
    try {
      setLoading(true);
      await api.publishRoster(selectedRosterId);
      await loadRosters();
      await loadGrid(selectedRosterId, viewMode);
    } catch (err: any) {
      setError(err.message || 'Failed to publish roster');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateChild = async () => {
    if (!selectedRosterId) return;
    try {
      setLoading(true);
      const child = await api.createChildVersion(selectedRosterId);
      await loadRosters();
      setSelectedRosterId(child.id);
    } catch (err: any) {
      setError(err.message || 'Failed to create child version');
    } finally {
      setLoading(false);
    }
  };

  const openReassignModal = async (
    dateStr: string,
    bpId: string,
    brandName: string,
    procName: string,
    startTime: string,
    endTime: string,
    sourceEmpId?: string
  ) => {
    setReassignSlot({
      date: dateStr,
      brand_process_id: bpId,
      brand_name: brandName,
      process_name: procName,
      start_time: startTime,
      end_time: endTime,
      source_employee_id: sourceEmpId,
    });
    setReassignSuccessMsg(null);
    setConfirmCrossPod(false);

    try {
      const cands = await api.getBackupCandidates(
        selectedRosterId,
        bpId,
        dateStr,
        startTime + ':00',
        endTime + ':00'
      );
      setCandidates(cands);
      if (cands.length > 0) {
        setSelectedCandidateId(cands[0].employee_id);
      } else {
        setSelectedCandidateId('');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to discover backup candidates');
    }
  };

  const handleApplyReassignment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reassignSlot || !selectedCandidateId) return;

    try {
      setLoading(true);
      await api.applyReassignment({
        roster_id: selectedRosterId,
        date: reassignSlot.date,
        brand_process_id: reassignSlot.brand_process_id,
        start_time: reassignSlot.start_time + ':00',
        end_time: reassignSlot.end_time + ':00',
        target_employee_id: selectedCandidateId,
        source_employee_id: reassignSlot.source_employee_id,
        reason: reassignReason,
        confirm_cross_pod_approval: confirmCrossPod,
      });

      setReassignSuccessMsg('Successfully reassigned slot!');
      setTimeout(() => {
        setReassignSlot(null);
        setReassignSuccessMsg(null);
      }, 1000);

      await loadRosters();
      await loadGrid(selectedRosterId, viewMode);
    } catch (err: any) {
      setError(err.message || 'Reassignment application failed');
    } finally {
      setLoading(false);
    }
  };

  const currentRoster = rosters.find((r) => r.id === selectedRosterId);

  return (
    <div className="space-y-6">
      {/* Top Controls Bar */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Calendar className="w-6 h-6 text-indigo-600" />
          <div>
            <h1 className="text-xl font-bold text-slate-900">Roster Management</h1>
            <p className="text-xs text-slate-500">
              Deterministic generation, constraint validation, and five synchronized views
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedRosterId}
            onChange={(e) => setSelectedRosterId(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {rosters.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} (v{r.version} - {r.status})
              </option>
            ))}
          </select>

          <button
            onClick={() => setShowGenModal(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded-lg shadow-sm transition"
          >
            + Generate Roster
          </button>

          {currentRoster?.status !== 'PUBLISHED' ? (
            <button
              onClick={handlePublish}
              disabled={currentRoster?.status === 'STALE' || (currentRoster?.hard_violations_count ?? 0) > 0}
              className={`px-4 py-2 font-medium text-sm rounded-lg shadow-sm flex items-center gap-2 transition ${currentRoster?.status === 'STALE' || (currentRoster?.hard_violations_count ?? 0) > 0
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                }`}
            >
              <Lock className="w-4 h-4" /> Publish Roster
            </button>
          ) : (
            <button
              onClick={handleCreateChild}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm rounded-lg shadow-sm flex items-center gap-2 transition"
            >
              <GitBranch className="w-4 h-4" /> Spawn Modifiable Version
            </button>
          )}
        </div>
      </div>

      {/* Roster Status & Conflict Warning Header */}
      {currentRoster && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between gap-4 ${currentRoster.status === 'PUBLISHED'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : currentRoster.status === 'STALE'
                ? 'bg-amber-50 border-amber-200 text-amber-900'
                : currentRoster.hard_violations_count > 0
                  ? 'bg-rose-50 border-rose-200 text-rose-900'
                  : 'bg-blue-50 border-blue-200 text-blue-900'
            }`}
        >
          <div className="flex items-center gap-3">
            {currentRoster.status === 'PUBLISHED' ? (
              <CheckCircle className="w-5 h-5 text-emerald-600" />
            ) : currentRoster.status === 'STALE' ? (
              <AlertTriangle className="w-5 h-5 text-amber-600" />
            ) : currentRoster.hard_violations_count > 0 ? (
              <ShieldAlert className="w-5 h-5 text-rose-600" />
            ) : (
              <CheckCircle className="w-5 h-5 text-blue-600" />
            )}
            <div>
              <span className="font-semibold text-sm">Status: {currentRoster.status}</span>
              <span className="text-xs ml-3 opacity-80">
                Version {currentRoster.version} | Total Shifts: {currentRoster.total_shifts} | Allocations:{' '}
                {currentRoster.total_allocations}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-medium">
            <span
              className={`px-2.5 py-1 rounded-full ${currentRoster.hard_violations_count > 0
                  ? 'bg-rose-200 text-rose-800 font-bold'
                  : 'bg-slate-100 text-slate-700'
                }`}
            >
              {currentRoster.hard_violations_count} Hard Conflicts
            </span>
            <span className="px-2.5 py-1 bg-slate-100 text-slate-700 rounded-full">
              {currentRoster.soft_warnings_count} Soft Warnings
            </span>
          </div>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 text-sm rounded-xl flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-bold ml-4">
            ✕
          </button>
        </div>
      )}

      {/* The 5 Required Roster Viewing Modes Navigation */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div className="flex gap-2">
          {(
            [
              { id: 'company', label: '1. Company-wide' },
              { id: 'pod', label: '2. Pod-wise' },
              { id: 'brand', label: '3. Brand-wise' },
              { id: 'process', label: '4. Process-wise' },
              { id: 'employee', label: '5. Employee-wise' },
            ] as const
          ).map((mode) => (
            <button
              key={mode.id}
              onClick={() => setViewMode(mode.id)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${viewMode === mode.id
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
            >
              {mode.label}
            </button>
          ))}
        </div>
      </div>

      {/* Interactive Calendar Grid */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[1200px]">
            <thead>
              <tr className="bg-slate-100 text-slate-700 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                <th className="p-3 w-56 sticky left-0 bg-slate-100 z-10 border-r border-slate-200">
                  {viewMode === 'company' || viewMode === 'employee' || viewMode === 'pod'
                    ? 'Employee / Pod'
                    : viewMode === 'brand'
                      ? 'Brand / Process'
                      : 'Process / Brand'}
                </th>
                {gridData?.dates.map((d) => {
                  const dayNum = parseInt(d.split('-')[2], 10);
                  const dateObj = new Date(d);
                  const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6;
                  return (
                    <th
                      key={d}
                      className={`p-2 text-center border-r border-slate-200 min-w-[70px] ${isWeekend ? 'bg-amber-50/60 text-amber-900' : ''
                        }`}
                    >
                      <div>{dayNum}</div>
                      <div className="text-[10px] font-normal text-slate-500">
                        {dateObj.toLocaleDateString('en-US', { weekday: 'narrow' })}
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {gridData?.rows.map((row) => (
                <tr key={row.row_id} className="hover:bg-slate-50/80 transition">
                  {/* Sticky row label */}
                  <td className="p-3 sticky left-0 bg-white z-10 border-r border-slate-200 shadow-sm">
                    <div className="font-bold text-slate-900">{row.title}</div>
                    <div className="text-[11px] text-slate-500">{row.subtitle || row.group_name}</div>
                  </td>

                  {/* Day Cells */}
                  {gridData.dates.map((d) => {
                    const cell = row.days[d];
                    const isWeekend = cell && (cell.day_of_week === 5 || cell.day_of_week === 6);

                    if (!cell || !cell.is_working) {
                      return (
                        <td
                          key={d}
                          className={`p-1 text-center border-r border-slate-200 ${isWeekend ? 'bg-slate-50/80' : 'bg-slate-50/40'
                            }`}
                        >
                          <span className="text-[10px] text-slate-400 font-medium">OFF</span>
                        </td>
                      );
                    }

                    return (
                      <td
                        key={d}
                        className={`p-1 border-r border-slate-200 align-top ${isWeekend ? 'bg-amber-50/30' : ''
                          }`}
                      >
                        <div className="space-y-1">
                          {cell.allocations.map((a) => (
                            <div
                              key={a.allocation_id}
                              onClick={() => {
                                if (currentRoster?.status !== 'PUBLISHED') {
                                  openReassignModal(
                                    d,
                                    a.brand_process_id,
                                    a.brand_name,
                                    a.process_name,
                                    a.start_time,
                                    a.end_time,
                                    a.employee_id
                                  );
                                }
                              }}
                              className={`p-1 rounded text-[10px] font-medium border cursor-pointer hover:opacity-80 transition ${a.allocation_type === 'PRIMARY'
                                  ? 'bg-indigo-50 border-indigo-200 text-indigo-900'
                                  : a.allocation_type === 'SAME_POD_REASSIGNMENT'
                                    ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                                    : 'bg-purple-50 border-purple-200 text-purple-900 font-bold'
                                }`}
                              title={`Click to Reassign: ${a.brand_name} - ${a.process_name} (${a.start_time}-${a.end_time})`}
                            >
                              <div className="truncate font-semibold">{a.brand_name}</div>
                              <div className="truncate opacity-80">
                                {a.process_name} ({a.start_time}-{a.end_time})
                              </div>
                            </div>
                          ))}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Unresolved Conflict Panel */}
      {gridData && gridData.summary_conflicts.length > 0 && (
        <div className="bg-white border border-rose-200 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-rose-800 font-bold text-sm">
            <ShieldAlert className="w-5 h-5 text-rose-600" />
            Detected Roster Conflicts & Coverage Gaps ({gridData.summary_conflicts.length})
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
            {gridData.summary_conflicts.map((c) => (
              <div
                key={c.id}
                className="p-3 bg-rose-50/60 border border-rose-200 rounded-lg space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-rose-900">{c.conflict_type}</span>
                  <span className="text-[10px] bg-rose-200 text-rose-800 px-2 py-0.5 rounded-full font-bold">
                    {c.severity}
                  </span>
                </div>
                <div className="text-slate-700 font-medium">{c.description}</div>
                <div className="text-slate-500 text-[10px]">Date: {c.date}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generate Roster Modal */}
      {showGenModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900">Generate Monthly Roster</h2>
            <form onSubmit={handleGenerate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Roster Title</label>
                <input
                  type="text"
                  value={genName}
                  onChange={(e) => setGenName(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Month</label>
                  <input
                    type="number"
                    min="1"
                    max="12"
                    value={genMonth}
                    onChange={(e) => setGenMonth(parseInt(e.target.value, 10))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Year</label>
                  <input
                    type="number"
                    min="2020"
                    max="2030"
                    value={genYear}
                    onChange={(e) => setGenYear(parseInt(e.target.value, 10))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    required
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowGenModal(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg"
                >
                  {loading ? 'Generating...' : 'Start Deterministic Generation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Absence Reassignment Modal */}
      {reassignSlot && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg p-6 space-y-4">
            <div className="flex items-center gap-2 text-indigo-700 font-bold text-base">
              <ArrowRightLeft className="w-5 h-5" />
              Manual Reassignment & Backup Discovery
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
              <div>
                <span className="font-semibold text-slate-700">Target Process: </span>
                {reassignSlot.brand_name} — {reassignSlot.process_name}
              </div>
              <div>
                <span className="font-semibold text-slate-700">Interval: </span>
                {reassignSlot.date} ({reassignSlot.start_time} - {reassignSlot.end_time})
              </div>
            </div>

            {reassignSuccessMsg && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg font-medium">
                {reassignSuccessMsg}
              </div>
            )}

            <form onSubmit={handleApplyReassignment} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Eligible Backup Candidates ({candidates.length})
                </label>
                {candidates.length === 0 ? (
                  <p className="text-xs text-rose-600 italic">No eligible backup candidates found.</p>
                ) : (
                  <select
                    value={selectedCandidateId}
                    onChange={(e) => setSelectedCandidateId(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                    required
                  >
                    {candidates.map((c) => (
                      <option key={c.employee_id} value={c.employee_id}>
                        {c.name} ({c.is_same_pod ? 'Same Pod' : 'Cross-Pod'}
                        {c.requires_approval ? ' - Needs Manager Approval' : ''}
                        {c.prefers_off_on_day ? ' - Prefers Off Today' : ''})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {candidates.find((c) => c.employee_id === selectedCandidateId)?.requires_approval && (
                <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg space-y-2">
                  <span className="text-xs font-bold text-purple-900 block">
                    Cross-Pod Operations Manager Authorization
                  </span>
                  <label className="flex items-center gap-2 text-xs text-purple-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={confirmCrossPod}
                      onChange={(e) => setConfirmCrossPod(e.target.checked)}
                      className="rounded text-purple-600 focus:ring-purple-500"
                      required
                    />
                    I, as Operations Manager, explicitly authorize this cross-pod allocation.
                  </label>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Reassignment Reason</label>
                <input
                  type="text"
                  value={reassignReason}
                  onChange={(e) => setReassignReason(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  required
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setReassignSlot(null)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !selectedCandidateId}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm"
                >
                  Apply Reassignment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
