import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  Employee,
  Pod,
  Brand,
  ProcessItem,
  BrandProcess,
  RosterSummary,
  RosterGridView,
  RosterConflict,
} from '../services/types';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { NavTab } from '../components/layout/Sidebar';
import {
  Users,
  Network,
  Briefcase,
  Layers,
  Calendar,
  ShieldAlert,
  Sparkles,
  ArrowRightLeft,
  CheckCircle2,
  Clock,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';

interface DashboardScreenProps {
  rosters: RosterSummary[];
  selectedRosterId: string;
  onNavigate: (tab: NavTab) => void;
  onOpenGenerateModal: () => void;
}

export const DashboardScreen: React.FC<DashboardScreenProps> = ({
  rosters,
  selectedRosterId,
  onNavigate,
  onOpenGenerateModal,
}) => {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [pods, setPods] = useState<Pod[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [processes, setProcesses] = useState<ProcessItem[]>([]);
  const [gridData, setGridData] = useState<RosterGridView | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, [selectedRosterId]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [eList, pList, bList, prList] = await Promise.all([
        api.getEmployees(),
        api.getPods(),
        api.getBrands(),
        api.getProcesses(),
      ]);
      setEmployees(eList);
      setPods(pList);
      setBrands(bList);
      setProcesses(prList);

      if (selectedRosterId) {
        const grid = await api.getRosterGrid(selectedRosterId, 'company');
        setGridData(grid);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const currentRoster = rosters.find((r) => r.id === selectedRosterId) || rosters[0];
  const conflicts = gridData?.summary_conflicts || [];
  const hardConflicts = conflicts.filter((c) => c.severity === 'HARD_VIOLATION');
  const softWarnings = conflicts.filter((c) => c.severity === 'SOFT_WARNING');

  // Compute coverage %
  const totalSlotsExpected = (currentRoster?.total_allocations || 0) + hardConflicts.length;
  const coveragePercent =
    totalSlotsExpected > 0
      ? Math.round(((currentRoster?.total_allocations || 0) / totalSlotsExpected) * 100)
      : 100;

  // Pod-wise employee breakdown
  const podDistribution = pods.map((p) => {
    const memberCount = employees.filter((e) => e.pod_id === p.id).length;
    return { id: p.id, name: p.name, count: memberCount };
  });

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-6 text-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-500/30 text-indigo-200 border border-indigo-400/30">
              Operations Control Center
            </span>
            {currentRoster && (
              <span className="text-xs font-mono text-slate-300">
                {currentRoster.name} (v{currentRoster.version})
              </span>
            )}
          </div>
          <h2 className="text-xl font-bold tracking-tight">Workforce Management Dashboard</h2>
          <p className="text-xs text-slate-300 max-w-xl leading-relaxed">
            Deterministic scheduling, pod allocations, interval validation, and real-time coverage exception monitoring across all operational brands.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate('roster')}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-800/80 hover:bg-slate-700/80 text-white rounded-xl text-xs font-semibold border border-slate-700 transition-all cursor-pointer"
          >
            <Calendar className="w-3.5 h-3.5 text-slate-300" />
            <span>Open Calendar</span>
          </button>
          <button
            onClick={onOpenGenerateModal}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-xs shadow-indigo-600/40 transition-all cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Generate Roster</span>
          </button>
        </div>
      </div>

      {/* 4 Primary Operational Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Active Workforce"
          value={employees.length}
          subtitle={`${pods.length} Operational Pods`}
          icon={<Users className="w-5 h-5 text-indigo-600" />}
          badge={{ text: '100% Active', variant: 'emerald' }}
        />
        <MetricCard
          title="Operational Brands"
          value={brands.length}
          subtitle={`${processes.length} Standard Processes`}
          icon={<Briefcase className="w-5 h-5 text-indigo-600" />}
          badge={{ text: 'Multi-Brand', variant: 'blue' }}
        />
        <MetricCard
          title="Roster Staffing Coverage"
          value={`${coveragePercent}%`}
          subtitle={`${currentRoster?.total_allocations || 0} process allocations`}
          icon={<TrendingUp className="w-5 h-5 text-indigo-600" />}
          progress={{ percentage: coveragePercent }}
        />
        <MetricCard
          title="Open Exceptions"
          value={conflicts.length}
          subtitle={`${hardConflicts.length} hard violations require action`}
          icon={<ShieldAlert className="w-5 h-5 text-rose-600" />}
          badge={
            hardConflicts.length > 0
              ? { text: `${hardConflicts.length} Action Needed`, variant: 'rose' }
              : { text: 'All Clear', variant: 'emerald' }
          }
        />
      </div>

      {/* Main Grid: Roster Status + Quick Actions + Conflicts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Roster Status & Pod Staffing */}
        <div className="lg:col-span-2 space-y-6">
          {/* Active Roster Operational Health */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-2xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="space-y-0.5">
                <h3 className="text-sm font-bold text-slate-900">Active Roster Health & Metrics</h3>
                <p className="text-xs text-slate-500">
                  {currentRoster?.name} (Version {currentRoster?.version})
                </p>
              </div>
              <div className="flex items-center gap-2">
                {currentRoster && <StatusBadge type="roster" status={currentRoster.status} size="md" />}
                <button
                  onClick={() => onNavigate('roster')}
                  className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1 cursor-pointer"
                >
                  View Details <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[11px] text-slate-500 font-medium">Total Shifts</span>
                <p className="text-lg font-bold text-slate-900 mt-0.5">
                  {currentRoster?.total_shifts ?? 0}
                </p>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[11px] text-slate-500 font-medium">Allocations</span>
                <p className="text-lg font-bold text-indigo-600 mt-0.5">
                  {currentRoster?.total_allocations ?? 0}
                </p>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[11px] text-slate-500 font-medium">Hard Violations</span>
                <p className="text-lg font-bold text-rose-600 mt-0.5">{hardConflicts.length}</p>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[11px] text-slate-500 font-medium">Soft Warnings</span>
                <p className="text-lg font-bold text-amber-600 mt-0.5">{softWarnings.length}</p>
              </div>
            </div>

            {/* Quick Pod Staffing Bars */}
            <div className="space-y-3 pt-2">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Pod Workforce Distribution
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {podDistribution.map((pod) => (
                  <div
                    key={pod.id}
                    className="p-3 rounded-lg border border-slate-200/70 bg-slate-50/50 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <Network className="w-4 h-4 text-indigo-600" />
                      <span className="text-xs font-semibold text-slate-800">{pod.name}</span>
                    </div>
                    <span className="text-xs font-bold text-slate-700 bg-white px-2 py-0.5 rounded-md border border-slate-200">
                      {pod.count} Employees
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Actions Panel */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-2xs space-y-3">
            <h3 className="text-sm font-bold text-slate-900">Operational Quick Actions</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <button
                onClick={onOpenGenerateModal}
                className="p-3 rounded-xl border border-slate-200 hover:border-indigo-500 hover:bg-indigo-50/40 text-left transition-all cursor-pointer group"
              >
                <Sparkles className="w-4 h-4 text-indigo-600 mb-2 group-hover:scale-110 transition-transform" />
                <span className="block text-xs font-bold text-slate-900">Generate Roster</span>
                <span className="text-[11px] text-slate-500">Run monthly engine</span>
              </button>
              <button
                onClick={() => onNavigate('conflicts')}
                className="p-3 rounded-xl border border-slate-200 hover:border-rose-500 hover:bg-rose-50/40 text-left transition-all cursor-pointer group"
              >
                <ShieldAlert className="w-4 h-4 text-rose-600 mb-2 group-hover:scale-110 transition-transform" />
                <span className="block text-xs font-bold text-slate-900">Review Conflicts</span>
                <span className="text-[11px] text-slate-500">Uncovered slots</span>
              </button>
              <button
                onClick={() => onNavigate('employees')}
                className="p-3 rounded-xl border border-slate-200 hover:border-blue-500 hover:bg-blue-50/40 text-left transition-all cursor-pointer group"
              >
                <Users className="w-4 h-4 text-blue-600 mb-2 group-hover:scale-110 transition-transform" />
                <span className="block text-xs font-bold text-slate-900">Add Employee</span>
                <span className="text-[11px] text-slate-500">Manage roster staff</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: High-Priority Conflict Feed */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-2xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600" />
                <h3 className="text-sm font-bold text-slate-900">Priority Exceptions</h3>
              </div>
              <button
                onClick={() => onNavigate('conflicts')}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold cursor-pointer"
              >
                View All ({conflicts.length})
              </button>
            </div>

            {conflicts.length === 0 ? (
              <div className="py-8 text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
                <p className="text-xs font-semibold text-slate-800">Zero Active Conflicts</p>
                <p className="text-[11px] text-slate-500">All shifts and allocations are fully covered.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {conflicts.slice(0, 4).map((c) => (
                  <div
                    key={c.id}
                    onClick={() => onNavigate('conflicts')}
                    className="p-3 rounded-lg border border-slate-200 hover:border-rose-400 bg-slate-50/50 hover:bg-white text-xs space-y-1.5 transition-all cursor-pointer"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900 truncate">{c.conflict_type}</span>
                      <StatusBadge type="conflict" status={c.severity} />
                    </div>
                    <p className="text-slate-600 text-[11px] line-clamp-2">{c.description}</p>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono pt-1 border-t border-slate-100">
                      <span>Date: {c.date}</span>
                      <span className="text-indigo-600 font-sans font-semibold">Reassign &rarr;</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

