import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { RosterSummary, WorkforceAnalytics } from '../services/types';
import { MetricCard } from '../components/common/MetricCard';
import {
  Users,
  Clock,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  ArrowRightLeft,
  ChevronRight,
  BrainCircuit,
  Network,
  Activity,
  Layers,
} from 'lucide-react';
import { NavTab } from '../components/layout/Sidebar';

interface AnalyticsScreenProps {
  rosters: RosterSummary[];
  selectedRosterId: string;
  onNavigateTab?: (tab: NavTab) => void;
}

export const AnalyticsScreen: React.FC<AnalyticsScreenProps> = ({
  rosters,
  selectedRosterId,
  onNavigateTab,
}) => {
  const [analytics, setAnalytics] = useState<WorkforceAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentRoster = rosters.find((r) => r.id === selectedRosterId) || rosters[0];

  useEffect(() => {
    if (selectedRosterId) {
      loadAnalytics(selectedRosterId);
    }
  }, [selectedRosterId]);

  const loadAnalytics = async (rosterId: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getRosterAnalytics(rosterId);
      setAnalytics(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load workforce analytics');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-2xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="p-1.5 bg-indigo-50 text-indigo-700 rounded-lg">
              <BrainCircuit className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Workforce Capacity & Pod Intelligence
            </h1>
            {currentRoster && (
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                {new Date(currentRoster.year, currentRoster.month - 1).toLocaleString('en-US', {
                  month: 'long',
                  year: 'numeric',
                })}{' '}
                · v{currentRoster.version}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500">
            Real-time analytics of pod capacity vs. demand, surplus/deficit staffing detection, and cross-pod rebalancing opportunities.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onNavigateTab && (
            <>
              <button
                onClick={() => onNavigateTab('roster')}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors cursor-pointer"
              >
                <span>Calendar</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => onNavigateTab('conflicts')}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-lg transition-colors cursor-pointer"
              >
                <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                <span>Conflicts</span>
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => currentRoster && loadAnalytics(currentRoster.id)}
            className="text-xs font-semibold text-rose-800 hover:underline"
          >
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="py-24 text-center space-y-3 bg-white rounded-2xl border border-slate-200/80">
          <div className="w-9 h-9 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-semibold text-slate-700">Calculating pod capacity and demand analytics...</p>
        </div>
      ) : analytics ? (
        <>
          {/* Executive KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Demand Slot Coverage"
              value={`${analytics.scheduled_allocations} / ${analytics.total_demand_slots}`}
              subtitle={`${analytics.demand_coverage_pct}% satisfied (${analytics.total_demand_slots - analytics.scheduled_allocations} uncovered)`}
              icon={<CheckCircle2 className="w-5 h-5 text-indigo-600" />}
              badge={{
                text: `${analytics.demand_coverage_pct}%`,
                variant: analytics.scheduled_allocations === analytics.total_demand_slots ? 'emerald' : 'amber',
              }}
            />
            <MetricCard
              title="Scheduled Demand Hours"
              value={`${analytics.scheduled_hours}h`}
              subtitle={`out of ${analytics.total_demand_hours}h total demand`}
              icon={<Clock className="w-5 h-5 text-blue-600" />}
              badge={{
                text: `${Math.round((analytics.scheduled_hours / (analytics.total_demand_hours || 1)) * 100)}%`,
                variant: 'blue',
              }}
            />
            <MetricCard
              title="Workforce Pool Utilization"
              value={`${analytics.workforce_utilization_pct}%`}
              subtitle={`${analytics.total_employees} agents (${analytics.total_capacity_hours}h capacity)`}
              icon={<Users className="w-5 h-5 text-emerald-600" />}
              badge={{
                text: `${analytics.total_employees} Staff`,
                variant: 'emerald',
              }}
            />
            <MetricCard
              title="Coverage Hard Conflicts"
              value={analytics.hard_conflicts_count}
              subtitle={analytics.hard_conflicts_count === 0 ? 'Zero constraint violations' : 'Requires ops intervention'}
              icon={<ShieldAlert className={`w-5 h-5 ${analytics.hard_conflicts_count === 0 ? 'text-emerald-600' : 'text-rose-600'}`} />}
              badge={{
                text: analytics.hard_conflicts_count === 0 ? 'Optimal' : `${analytics.hard_conflicts_count} Hard`,
                variant: analytics.hard_conflicts_count === 0 ? 'emerald' : 'rose',
              }}
            />
          </div>

          {/* Pod Capacity & Balance Cards */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <Network className="w-4 h-4 text-indigo-600" />
                  <span>Pod Capacity, Deficit & Surplus Analysis</span>
                </h2>
                <p className="text-xs text-slate-500">
                  Identifies which pods need additional employees and which pods have free employees available for cross-pod deployment.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {analytics.pods.map((pod) => {
                const isDeficit = pod.status === 'DEFICIT';
                const isSurplus = pod.status === 'SURPLUS';

                return (
                  <div
                    key={pod.pod_id}
                    className={`rounded-2xl border bg-white p-5 flex flex-col justify-between shadow-2xs transition-all hover:shadow-md ${
                      isDeficit
                        ? 'border-rose-200/80 ring-1 ring-rose-200/50'
                        : isSurplus
                        ? 'border-emerald-200/80 ring-1 ring-emerald-200/50'
                        : 'border-slate-200/80'
                    }`}
                  >
                    <div className="space-y-3">
                      {/* Pod Header & Status Badge */}
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h3 className="text-base font-bold text-slate-900">{pod.pod_name}</h3>
                          <p className="text-[11px] text-slate-500 font-medium">Lead: {pod.lead_name}</p>
                          <p className="text-[11px] text-slate-600 font-semibold mt-0.5">
                            {pod.employee_count} Agents Assigned
                          </p>
                        </div>
                        {isDeficit && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-rose-100 text-rose-700 border border-rose-200 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3 text-rose-600" />
                            DEFICIT
                          </span>
                        )}
                        {isSurplus && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                            <Sparkles className="w-3 h-3 text-emerald-600" />
                            SURPLUS
                          </span>
                        )}
                        {!isDeficit && !isSurplus && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-100 text-blue-700 border border-blue-200 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3 text-blue-600" />
                            BALANCED
                          </span>
                        )}
                      </div>

                      {/* Capacity Bar */}
                      <div className="space-y-1 pt-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-500 font-medium">Scheduled / Capacity:</span>
                          <span className="font-bold text-slate-900">
                            {pod.scheduled_hours}h / {pod.available_capacity_hours}h
                          </span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-2 rounded-full transition-all duration-500 ${
                              isDeficit
                                ? 'bg-rose-500'
                                : pod.utilization_pct > 80
                                ? 'bg-indigo-600'
                                : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(pod.utilization_pct, 100)}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-[11px]">
                          <span className="text-slate-400 font-mono">Utilization</span>
                          <span
                            className={`font-mono font-bold ${
                              isDeficit
                                ? 'text-rose-700'
                                : pod.utilization_pct > 80
                                ? 'text-indigo-700'
                                : 'text-emerald-700'
                            }`}
                          >
                            {pod.utilization_pct}%
                          </span>
                        </div>
                      </div>

                      {/* Staffing Requirement Alert */}
                      <div className="pt-2 border-t border-slate-100">
                        {isDeficit && (
                          <div className="p-2 rounded-lg bg-rose-50/80 border border-rose-200 text-rose-800 text-xs space-y-1">
                            <div className="font-bold flex items-center gap-1.5">
                              <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                              <span>Needs +{pod.employees_needed} Employee(s)</span>
                            </div>
                            <p className="text-[11px] text-rose-700 leading-tight">
                              Demand exceeds capacity by +{Math.abs(pod.net_hours_gap)} hours. Requires external borrowing or hiring.
                            </p>
                          </div>
                        )}
                        {isSurplus && (
                          <div className="p-2 rounded-lg bg-emerald-50/80 border border-emerald-200 text-emerald-800 text-xs space-y-1">
                            <div className="font-bold flex items-center gap-1.5">
                              <Sparkles className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                              <span>Has ~{pod.free_employees_count} Free Employee(s)</span>
                            </div>
                            <p className="text-[11px] text-emerald-700 leading-tight">
                              Available surplus of {Math.abs(pod.net_hours_gap)} capacity hours. Can cover other pods.
                            </p>
                          </div>
                        )}
                        {!isDeficit && !isSurplus && (
                          <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 text-xs">
                            <div className="font-semibold text-slate-800">Balanced Capacity</div>
                            <p className="text-[11px] text-slate-500 mt-0.5">
                              Pod shifts closely match contracted capacity hours.
                            </p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Skill Summary */}
                    <div className="pt-3 border-t border-slate-100 mt-3">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Skill Capabilities ({pod.skills_summary.length})
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {pod.skills_summary.slice(0, 4).map((sk) => (
                          <span
                            key={sk}
                            className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-medium"
                          >
                            {sk}
                          </span>
                        ))}
                        {pod.skills_summary.length > 4 && (
                          <span className="px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded text-[10px] font-medium">
                            +{pod.skills_summary.length - 4} more
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Actionable Recommendations Panel */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-3">
            <div className="flex items-center gap-2">
              <span className="p-1.5 bg-indigo-50 text-indigo-700 rounded-lg">
                <TrendingUp className="w-4 h-4" />
              </span>
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Workforce Optimization & Rebalancing Recommendations
              </h3>
            </div>

            <div className="space-y-2">
              {analytics.recommendations.map((rec, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-50/80 border border-slate-200/70 text-xs text-slate-800"
                >
                  <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-[10px] shrink-0 mt-0.5">
                    {i + 1}
                  </span>
                  <p className="leading-relaxed font-medium">{rec}</p>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
};
