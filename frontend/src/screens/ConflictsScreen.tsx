import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  RosterSummary,
  RosterGridView,
  RosterConflict,
  ResolverPreviewResponse,
  ResolverBundle,
} from '../services/types';
import { StatusBadge } from '../components/common/StatusBadge';
import { ReassignmentModal } from '../components/roster/ReassignmentModal';
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Clock,
  ArrowRightLeft,
  Filter,
  Search,
  RefreshCw,
  Sparkles,
  Zap,
  CheckSquare,
  Square,
  AlertCircle,
  HelpCircle,
  TrendingUp,
  Cpu,
  Layers,
  ChevronRight,
  UserCheck,
} from 'lucide-react';

interface ConflictsScreenProps {
  rosters: RosterSummary[];
  selectedRosterId: string;
  onRefreshRosters: () => void;
}

export const ConflictsScreen: React.FC<ConflictsScreenProps> = ({
  rosters,
  selectedRosterId,
  onRefreshRosters,
}) => {
  const [gridData, setGridData] = useState<RosterGridView | null>(null);
  const [loading, setLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'HARD_VIOLATION' | 'SOFT_WARNING'>('ALL');
  const [searchFilter, setSearchFilter] = useState('');

  // Resolver State
  const [resolverPreview, setResolverPreview] = useState<ResolverPreviewResponse | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [applying, setApplying] = useState(false);
  const [activeTab, setActiveTab] = useState<'AUTO' | 'APPROVAL' | 'UNRESOLVED' | 'RAW'>('AUTO');
  const [selectedBundleIds, setSelectedBundleIds] = useState<string[]>([]);
  const [applyResultBanner, setApplyResultBanner] = useState<string | null>(null);

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
  const [isReassignOpen, setIsReassignOpen] = useState(false);

  const currentRoster = rosters.find((r) => r.id === selectedRosterId) || rosters[0];

  useEffect(() => {
    if (selectedRosterId) {
      loadConflicts();
      // Reset preview on roster change
      setResolverPreview(null);
      setApplyResultBanner(null);
    }
  }, [selectedRosterId]);

  const loadConflicts = async () => {
    if (!selectedRosterId) return;
    try {
      setLoading(true);
      const data = await api.getRosterGrid(selectedRosterId, 'company');
      setGridData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeConflicts = async () => {
    if (!selectedRosterId) return;
    try {
      setAnalyzing(true);
      setApplyResultBanner(null);
      const res = await api.previewConflictResolutions(selectedRosterId);
      setResolverPreview(res);
      // Preselect all pending approval bundles by default
      setSelectedBundleIds(res.pending_approval_bundles.map((b) => b.bundle_id));
      if (res.automatically_resolvable_bundles.length > 0) {
        setActiveTab('AUTO');
      } else if (res.pending_approval_bundles.length > 0) {
        setActiveTab('APPROVAL');
      } else if (res.unresolvable_shortages.length > 0) {
        setActiveTab('UNRESOLVED');
      }
    } catch (err: any) {
      console.error(err);
      alert(`Error analyzing conflicts: ${err.message || 'Unknown error'}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleApplyResolutions = async (includeCrossPod: boolean) => {
    if (!selectedRosterId) return;
    try {
      setApplying(true);
      const res = await api.applyConflictResolutions({
        roster_id: selectedRosterId,
        approve_cross_pod: includeCrossPod,
        approved_bundle_ids: includeCrossPod ? selectedBundleIds : [],
        create_child_if_published: true,
      });

      setApplyResultBanner(
        `Successfully applied ${res.applied_bundles_count} resolution bundles (${res.applied_changes_count} changes). ` +
          (res.is_new_version
            ? `Original published roster preserved; created Child Revision v${res.version}.`
            : `Roster coverage updated to ${res.coverage_pct}%.`)
      );

      // Refresh conflicts and rosters
      await loadConflicts();
      onRefreshRosters();
      setResolverPreview(null);
    } catch (err: any) {
      console.error(err);
      alert(`Failed to apply resolutions: ${err.message || 'Validation error'}`);
    } finally {
      setApplying(false);
    }
  };

  const toggleBundleSelection = (bundleId: string) => {
    setSelectedBundleIds((prev) =>
      prev.includes(bundleId) ? prev.filter((id) => id !== bundleId) : [...prev, bundleId]
    );
  };

  const selectAllApprovalBundles = () => {
    if (!resolverPreview) return;
    if (selectedBundleIds.length === resolverPreview.pending_approval_bundles.length) {
      setSelectedBundleIds([]);
    } else {
      setSelectedBundleIds(resolverPreview.pending_approval_bundles.map((b) => b.bundle_id));
    }
  };

  const conflicts = gridData?.summary_conflicts || [];
  const hardViolations = conflicts.filter((c) => c.severity === 'HARD_VIOLATION');
  const softWarnings = conflicts.filter((c) => c.severity === 'SOFT_WARNING');

  const filteredConflicts = conflicts.filter((c) => {
    if (severityFilter !== 'ALL' && c.severity !== severityFilter) return false;
    if (searchFilter) {
      const q = searchFilter.toLowerCase();
      return (
        c.conflict_type.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q) ||
        c.date.includes(q)
      );
    }
    return true;
  });

  const handleOpenReassign = (c: RosterConflict) => {
    setReassignSlot({
      date: c.date,
      brand_process_id: c.brand_process_id || '',
      brand_name: 'Brand Demand',
      process_name: 'Coverage Process',
      start_time: c.start_time || '09:00:00',
      end_time: c.end_time || '18:00:00',
      source_employee_id: c.employee_id || undefined,
    });
    setIsReassignOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Automated Conflict Resolver Workspace Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl border border-indigo-900/50 p-6 text-white shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1.5">
                <Cpu className="w-3 h-3 text-indigo-400" /> CP-SAT Constraint Engine
              </span>
              {currentRoster?.status === 'PUBLISHED' && (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Published Roster (Safe Child Versioning)
                </span>
              )}
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2.5">
              Automated Constraint-Based Conflict Resolver
            </h2>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Synthesizes globally optimal reassignments across same-pod and authorized cross-pod staff using
              lexicographic optimization: 1) Staff positions, 2) Full slot demand, 3) Cross-pod minimization,
              4) Baseline churn minimization, and 5) Weekly-off soft preferences.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleAnalyzeConflicts}
              disabled={analyzing || loading}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/30 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 cursor-pointer"
            >
              <Sparkles className={`w-4 h-4 ${analyzing ? 'animate-spin' : ''}`} />
              <span>{analyzing ? 'Analyzing Constraints...' : 'Analyze Conflicts'}</span>
            </button>

            {resolverPreview && (
              <button
                onClick={() => handleApplyResolutions(true)}
                disabled={applying || (resolverPreview.resolvable_conflicts_count === 0 && selectedBundleIds.length === 0)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-md shadow-emerald-600/30 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 cursor-pointer"
              >
                <Zap className={`w-4 h-4 ${applying ? 'animate-spin' : ''}`} />
                <span>{applying ? 'Applying Transaction...' : 'Resolve All (Apply)'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Resolver Preview KPI Row */}
        {resolverPreview && (
          <div className="mt-6 pt-5 border-t border-indigo-800/40 grid grid-cols-2 sm:grid-cols-5 gap-4">
            <div className="bg-white/5 border border-white/10 rounded-xl p-3">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Solver Status
              </span>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-sm font-bold text-white">{resolverPreview.status}</span>
              </div>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-3">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Initial Conflicts
              </span>
              <p className="text-base font-bold text-rose-300 mt-1">
                {resolverPreview.initial_conflicts_count}
              </p>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-3">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Auto-Resolvable (Same-Pod)
              </span>
              <p className="text-base font-bold text-emerald-300 mt-1">
                {resolverPreview.automatically_resolvable_bundles.length}
              </p>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-3">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Pending Approval (Cross-Pod)
              </span>
              <p className="text-base font-bold text-amber-300 mt-1">
                {resolverPreview.pending_approval_bundles.length}
              </p>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-3">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Coverage Gain
              </span>
              <div className="flex items-center gap-1.5 mt-1">
                <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-sm font-bold text-white">
                  {resolverPreview.coverage_before_pct}% →{' '}
                  <span className="text-emerald-400">{resolverPreview.coverage_after_pct}%</span>
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Applied Result Alert Banner */}
      {applyResultBanner && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start gap-3 shadow-sm animate-in fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="text-xs text-emerald-900 leading-relaxed font-medium">
            {applyResultBanner}
          </div>
        </div>
      )}

      {/* Resolver Tabs */}
      {resolverPreview && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-2 shadow-2xs flex flex-wrap items-center gap-2">
          <button
            onClick={() => setActiveTab('AUTO')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === 'AUTO'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200/70'
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Automatically Resolved (Same-Pod)</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                activeTab === 'AUTO' ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-700'
              }`}
            >
              {resolverPreview.automatically_resolvable_bundles.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('APPROVAL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === 'APPROVAL'
                ? 'bg-amber-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200/70'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Pending Manager Approval (Cross-Pod)</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                activeTab === 'APPROVAL' ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-700'
              }`}
            >
              {resolverPreview.pending_approval_bundles.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('UNRESOLVED')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === 'UNRESOLVED'
                ? 'bg-rose-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200/70'
            }`}
          >
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Unresolved Shortages (Root Causes)</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                activeTab === 'UNRESOLVED' ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-700'
              }`}
            >
              {resolverPreview.unresolvable_shortages.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('RAW')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === 'RAW'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200/70'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>All Exceptions & Raw Conflicts</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                activeTab === 'RAW' ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-700'
              }`}
            >
              {conflicts.length}
            </span>
          </button>
        </div>
      )}

      {/* TAB 1: Automatically Resolvable Bundles (Same-Pod) */}
      {resolverPreview && activeTab === 'AUTO' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-emerald-600" />
              Verified Same-Pod Reassignments ({resolverPreview.automatically_resolvable_bundles.length})
            </h3>
            <button
              onClick={() => handleApplyResolutions(false)}
              disabled={applying || resolverPreview.automatically_resolvable_bundles.length === 0}
              className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Apply All Same-Pod Resolutions</span>
            </button>
          </div>

          {resolverPreview.automatically_resolvable_bundles.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200/80 p-8 text-center text-xs text-slate-500">
              No same-pod bundles required.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {resolverPreview.automatically_resolvable_bundles.map((bundle) => (
                <div
                  key={bundle.bundle_id}
                  className="bg-white rounded-xl border border-emerald-200/80 p-4 shadow-2xs hover:border-emerald-300 transition-all space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      {bundle.affected_dates.join(', ')}
                    </span>
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      Same-Pod Verified
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">{bundle.explanation}</p>

                  <div className="space-y-2 pt-2 border-t border-slate-100">
                    {bundle.changes.map((ch, idx) => (
                      <div
                        key={idx}
                        className="bg-slate-50/80 rounded-lg p-2.5 border border-slate-200/60 flex items-center justify-between text-xs"
                      >
                        <div>
                          <span className="font-semibold text-slate-800">
                            {ch.brand_name} - {ch.process_name}
                          </span>
                          <div className="text-[11px] text-slate-500 flex items-center gap-1 mt-0.5">
                            <Clock className="w-3 h-3 text-slate-400" />
                            {ch.start_time} - {ch.end_time}
                          </div>
                        </div>

                        <div className="text-right">
                          <span className="font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md border border-indigo-200 text-[11px]">
                            {ch.new_employee_name || 'Assigned Agent'}
                          </span>
                          <span className="block text-[10px] text-slate-400 mt-0.5">
                            {ch.new_employee_pod || 'Same Pod'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Pending Approval Bundles (Cross-Pod) */}
      {resolverPreview && activeTab === 'APPROVAL' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-amber-600" />
                Cross-Pod Candidate Bundles Requiring Manager Sign-Off (
                {resolverPreview.pending_approval_bundles.length})
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Select cross-pod candidates to authorize and deploy into the roster revision.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={selectAllApprovalBundles}
                className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5"
              >
                {selectedBundleIds.length === resolverPreview.pending_approval_bundles.length ? (
                  <CheckSquare className="w-3.5 h-3.5 text-indigo-600" />
                ) : (
                  <Square className="w-3.5 h-3.5 text-slate-400" />
                )}
                <span>Select All</span>
              </button>

              <button
                onClick={() => handleApplyResolutions(true)}
                disabled={applying || selectedBundleIds.length === 0}
                className="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>Approve & Apply Selected ({selectedBundleIds.length})</span>
              </button>
            </div>
          </div>

          {resolverPreview.pending_approval_bundles.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200/80 p-8 text-center text-xs text-slate-500">
              No cross-pod reassignments proposed.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {resolverPreview.pending_approval_bundles.map((bundle) => {
                const isSelected = selectedBundleIds.includes(bundle.bundle_id);
                return (
                  <div
                    key={bundle.bundle_id}
                    onClick={() => toggleBundleSelection(bundle.bundle_id)}
                    className={`bg-white rounded-xl border p-4 shadow-2xs transition-all cursor-pointer space-y-3 ${
                      isSelected
                        ? 'border-amber-400 ring-1 ring-amber-500/20 bg-amber-50/20'
                        : 'border-slate-200/80 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-amber-600" />
                        ) : (
                          <Square className="w-4 h-4 text-slate-400" />
                        )}
                        <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          {bundle.affected_dates.join(', ')}
                        </span>
                      </div>
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                        Cross-Pod Approval Required
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed">{bundle.explanation}</p>

                    <div className="space-y-2 pt-2 border-t border-slate-100">
                      {bundle.changes.map((ch, idx) => (
                        <div
                          key={idx}
                          className="bg-white rounded-lg p-2.5 border border-amber-200/60 flex items-center justify-between text-xs"
                        >
                          <div>
                            <span className="font-semibold text-slate-800">
                              {ch.brand_name} - {ch.process_name}
                            </span>
                            <div className="text-[11px] text-slate-500 flex items-center gap-1 mt-0.5">
                              <Clock className="w-3 h-3 text-slate-400" />
                              {ch.start_time} - {ch.end_time}
                            </div>
                          </div>

                          <div className="text-right">
                            <span className="font-bold text-amber-800 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200 text-[11px]">
                              {ch.new_employee_name || 'Cross-Pod Agent'}
                            </span>
                            <span className="block text-[10px] text-amber-600 font-semibold mt-0.5">
                              from {ch.new_employee_pod || 'Foreign Pod'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Unresolved Conflicts (Root Causes) */}
      {resolverPreview && activeTab === 'UNRESOLVED' && (
        <div className="space-y-4">
          <div>
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4 text-rose-600" />
              Mathematically Unresolvable Shortages ({resolverPreview.unresolvable_shortages.length})
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Identified demand slots where available certified workforce is mathematically insufficient.
            </p>
          </div>

          {resolverPreview.unresolvable_shortages.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200/80 p-8 text-center text-xs text-emerald-600 font-semibold">
              Zero unresolvable shortages! All demand slots are covered by the engine.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {resolverPreview.unresolvable_shortages.map((s, idx) => (
                <div
                  key={idx}
                  className="bg-white rounded-xl border border-rose-200/80 p-4 shadow-2xs space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      {s.date}
                    </span>
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                      Workforce Shortage
                    </span>
                  </div>

                  <div>
                    <h4 className="font-bold text-slate-800 text-xs">
                      {s.brand_name} - {s.process_name}
                    </h4>
                    <p className="text-xs text-slate-600 mt-1">{s.explanation}</p>
                  </div>

                  <div className="bg-slate-50 rounded-lg p-2.5 border border-slate-200/60 text-[11px] text-slate-600 space-y-1">
                    <div className="font-semibold text-slate-700">Root Cause Diagnostics:</div>
                    <ul className="list-disc list-inside text-slate-500 space-y-0.5">
                      <li>All primary certified employees are on approved leave or capacity exhausted.</li>
                      <li>Cross-pod certified candidates do not have required process skill certification.</li>
                      <li>Recommend hiring or training additional certified staff.</li>
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Raw Exceptions Feed (Existing Detailed Table) */}
      {(!resolverPreview || activeTab === 'RAW') && (
        <div className="space-y-4">
          {/* Metric Breakdown Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div
              onClick={() => setSeverityFilter('ALL')}
              className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                severityFilter === 'ALL'
                  ? 'bg-indigo-50/50 border-indigo-400 ring-1 ring-indigo-500/20'
                  : 'bg-white border-slate-200/80 hover:border-slate-300'
              }`}
            >
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Total Flagged Exceptions
              </span>
              <p className="text-2xl font-bold text-slate-900 mt-1">{conflicts.length}</p>
              <span className="text-xs text-slate-500 mt-0.5 block">All detected constraint warnings</span>
            </div>

            <div
              onClick={() => setSeverityFilter('HARD_VIOLATION')}
              className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                severityFilter === 'HARD_VIOLATION'
                  ? 'bg-rose-50/50 border-rose-400 ring-1 ring-rose-500/20'
                  : 'bg-white border-slate-200/80 hover:border-slate-300'
              }`}
            >
              <span className="text-[10px] font-bold text-rose-600 uppercase tracking-wider flex items-center gap-1">
                <ShieldAlert className="w-3 h-3" /> Hard Violations (Blockers)
              </span>
              <p className="text-2xl font-bold text-rose-700 mt-1">{hardViolations.length}</p>
              <span className="text-xs text-rose-600/80 mt-0.5 block">Must be resolved to publish</span>
            </div>

            <div
              onClick={() => setSeverityFilter('SOFT_WARNING')}
              className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                severityFilter === 'SOFT_WARNING'
                  ? 'bg-amber-50/50 border-amber-400 ring-1 ring-amber-500/20'
                  : 'bg-white border-slate-200/80 hover:border-slate-300'
              }`}
            >
              <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Soft Warnings
              </span>
              <p className="text-2xl font-bold text-amber-700 mt-1">{softWarnings.length}</p>
              <span className="text-xs text-amber-700/80 mt-0.5 block">Weekly-off preference mismatches</span>
            </div>
          </div>

          {/* Filter Toolbar */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-3 shadow-2xs flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-xs font-semibold text-slate-600">Filter by Severity:</span>
              {(['ALL', 'HARD_VIOLATION', 'SOFT_WARNING'] as const).map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  className={`px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                    severityFilter === sev
                      ? 'bg-indigo-600 text-white shadow-2xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200/60'
                  }`}
                >
                  {sev === 'ALL' ? 'All' : sev === 'HARD_VIOLATION' ? 'Hard Violations' : 'Soft Warnings'}
                </button>
              ))}
            </div>

            <div className="relative w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search by date, type, reason..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full pl-8.5 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder:text-slate-400 focus:outline-hidden focus:border-indigo-500 focus:bg-white"
              />
            </div>
          </div>

          {/* Conflict Cards Feed */}
          {loading ? (
            <div className="py-20 text-center space-y-2">
              <div className="w-7 h-7 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-slate-500">Scanning roster against independent validator...</p>
            </div>
          ) : filteredConflicts.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200/80 p-12 text-center space-y-3">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto" />
              <h3 className="text-sm font-bold text-slate-900">Zero Exceptions for Selected Filter</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                All required interval demands and employee constraints are fully satisfied.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredConflicts.map((c) => {
                const isHard = c.severity === 'HARD_VIOLATION';
                return (
                  <div
                    key={c.id}
                    className={`p-4.5 rounded-xl border bg-white shadow-2xs transition-all space-y-3 ${
                      isHard ? 'border-l-4 border-l-rose-600' : 'border-l-4 border-l-amber-500'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 text-sm">{c.conflict_type}</span>
                        <StatusBadge type="conflict" status={c.severity} />
                      </div>
                      <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span className="font-semibold text-slate-700">{c.date}</span>
                        {c.start_time && c.end_time && (
                          <span className="bg-slate-100 px-2 py-0.5 rounded-md text-[11px]">
                            {c.start_time} - {c.end_time}
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-slate-700 leading-relaxed">{c.description}</p>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                      <div className="text-[11px] text-slate-500">
                        Operational Impact:{' '}
                        <span className="font-medium text-slate-700">
                          {isHard ? 'Shortfall in minimum staffing' : 'Employee preferred day-off infringed'}
                        </span>
                      </div>

                      {c.brand_process_id && (
                        <button
                          onClick={() => handleOpenReassign(c)}
                          className="flex items-center gap-1.5 px-3 py-1 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 font-semibold rounded-lg text-xs transition-colors cursor-pointer"
                        >
                          <ArrowRightLeft className="w-3.5 h-3.5" />
                          <span>Reassign Slot</span>
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Manual Reassignment Modal */}
      {reassignSlot && (
        <ReassignmentModal
          isOpen={isReassignOpen}
          onClose={() => setIsReassignOpen(false)}
          rosterId={selectedRosterId}
          slot={reassignSlot}
          onReassigned={loadConflicts}
        />
      )}
    </div>
  );
};
