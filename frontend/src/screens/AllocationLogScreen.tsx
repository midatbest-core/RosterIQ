import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { RosterSummary, AllocationLogItem } from '../services/types';
import { StatusBadge } from '../components/common/StatusBadge';
import { MetricCard } from '../components/common/MetricCard';
import {
  ArrowRightLeft,
  ShieldCheck,
  ShieldAlert,
  Search,
  Filter,
  RefreshCw,
  Clock,
  Calendar,
  Briefcase,
  Layers,
  UserCheck,
  CheckCircle2,
} from 'lucide-react';

interface AllocationLogScreenProps {
  rosters: RosterSummary[];
  selectedRosterId: string;
}

export const AllocationLogScreen: React.FC<AllocationLogScreenProps> = ({
  rosters,
  selectedRosterId,
}) => {
  const [logs, setLogs] = useState<AllocationLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<'ALL' | 'CROSS_POD' | 'SAME_POD'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const currentRoster = rosters.find((r) => r.id === selectedRosterId) || rosters[0];

  useEffect(() => {
    if (selectedRosterId) {
      loadLogs();
    }
  }, [selectedRosterId]);

  const loadLogs = async () => {
    if (!selectedRosterId) return;
    try {
      setLoading(true);
      const data = await api.getAllocationLog(selectedRosterId, true);
      setLogs(data);
    } catch (err) {
      console.error('Failed to load allocation log:', err);
    } finally {
      setLoading(false);
    }
  };

  const crossPodCount = logs.filter((l) => l.allocation_type === 'CROSS_POD_REASSIGNMENT').length;
  const samePodCount = logs.filter((l) => l.allocation_type === 'SAME_POD_REASSIGNMENT').length;
  const managerApprovals = logs.filter((l) => l.is_cross_pod_approved).length;

  const filteredLogs = logs.filter((item) => {
    if (filterType === 'CROSS_POD' && item.allocation_type !== 'CROSS_POD_REASSIGNMENT') return false;
    if (filterType === 'SAME_POD' && item.allocation_type !== 'SAME_POD_REASSIGNMENT') return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        item.employee_name.toLowerCase().includes(q) ||
        item.brand_name.toLowerCase().includes(q) ||
        item.process_name.toLowerCase().includes(q) ||
        (item.reassigned_from_employee_name && item.reassigned_from_employee_name.toLowerCase().includes(q)) ||
        (item.reassignment_reason && item.reassignment_reason.toLowerCase().includes(q)) ||
        (item.approved_by_email && item.approved_by_email.toLowerCase().includes(q)) ||
        item.date.includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ArrowRightLeft className="w-5 h-5 text-indigo-600" />
            <h2 className="text-base font-bold text-slate-900">Dynamic Allocation & Reassignment Log</h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Immutable audit record of all backup allocations, cross-pod managerial approvals, and conflict-driven shift adjustments.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadLogs}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Log</span>
          </button>
        </div>
      </div>

      {/* KPI Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <MetricCard
          title="Total Dynamic Allocations"
          value={logs.length}
          subtitle="Non-primary reassignments"
          icon={<ArrowRightLeft className="w-5 h-5 text-indigo-600" />}
          badge={{ text: 'Live Log', variant: 'blue' }}
        />
        <MetricCard
          title="Same-Pod Backups"
          value={samePodCount}
          subtitle="Autonomous pod coverage"
          icon={<UserCheck className="w-5 h-5 text-sky-600" />}
          badge={{ text: 'Auto-Eligible', variant: 'emerald' }}
        />
        <MetricCard
          title="Cross-Pod Reassignments"
          value={crossPodCount}
          subtitle="Inter-pod workforce sharing"
          icon={<ShieldAlert className="w-5 h-5 text-purple-600" />}
          badge={{ text: 'Gated', variant: 'amber' }}
        />
        <MetricCard
          title="Ops Manager Authorizations"
          value={managerApprovals}
          subtitle="100% authenticated approvals"
          icon={<ShieldCheck className="w-5 h-5 text-emerald-600" />}
          badge={{ text: 'Audited', variant: 'emerald' }}
        />
      </div>

      {/* Filter & Search Toolbar */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-3 shadow-2xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-xs font-semibold text-slate-600">Filter By Type:</span>
          {(['ALL', 'CROSS_POD', 'SAME_POD'] as const).map((ft) => (
            <button
              key={ft}
              onClick={() => setFilterType(ft)}
              className={`px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                filterType === ft
                  ? 'bg-indigo-600 text-white shadow-2xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200/60'
              }`}
            >
              {ft === 'ALL'
                ? `All (${logs.length})`
                : ft === 'CROSS_POD'
                ? `Cross-Pod (${crossPodCount})`
                : `Same-Pod (${samePodCount})`}
            </button>
          ))}
        </div>

        <div className="relative w-72">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search employee, brand, reason, approver..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8.5 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder:text-slate-400 focus:outline-hidden focus:border-indigo-500 focus:bg-white"
          />
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden">
        {loading ? (
          <div className="py-20 text-center space-y-2">
            <div className="w-7 h-7 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-slate-500">Querying dynamic allocation audit trail...</p>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <CheckCircle2 className="w-9 h-9 text-slate-300 mx-auto" />
            <p className="text-xs font-semibold text-slate-700">No dynamic allocation logs found</p>
            <p className="text-[11px] text-slate-400">
              {searchQuery ? 'Try clearing your search query.' : 'Apply reassignments to populate the audit log.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto max-h-[65vh]">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-slate-50/95 backdrop-blur-xs border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px] z-10">
                <tr>
                  <th className="px-4 py-3">Calendar Date & Time</th>
                  <th className="px-4 py-3">Brand & Process</th>
                  <th className="px-4 py-3">Assigned Backup</th>
                  <th className="px-4 py-3">Absentee Replaced</th>
                  <th className="px-4 py-3">Allocation Type</th>
                  <th className="px-4 py-3">Audit Reason</th>
                  <th className="px-4 py-3">Manager Authorization</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredLogs.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-4 py-3 font-mono">
                      <div className="font-bold text-slate-900">{item.date}</div>
                      <div className="text-[10px] text-slate-500">
                        {item.start_time} - {item.end_time}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">{item.brand_name}</div>
                      <div className="text-[11px] text-indigo-600 font-medium">{item.process_name}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">{item.employee_name}</div>
                      {item.employee_pod_name && (
                        <div className="text-[10px] text-slate-500">{item.employee_pod_name}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-700">
                      {item.reassigned_from_employee_name ? (
                        <span className="font-medium text-slate-800">
                          {item.reassigned_from_employee_name}
                        </span>
                      ) : (
                        <span className="text-slate-400 italic">Direct Uncovered Slot</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge type="allocation" status={item.allocation_type} />
                    </td>
                    <td className="px-4 py-3 text-slate-600 text-[11px] max-w-[200px] truncate" title={item.reassignment_reason || ''}>
                      {item.reassignment_reason || '—'}
                    </td>
                    <td className="px-4 py-3">
                      {item.is_cross_pod_approved ? (
                        <div className="space-y-0.5">
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-md border border-purple-200">
                            <ShieldCheck className="w-3 h-3 text-purple-600" />
                            Approved
                          </span>
                          {item.approved_by_email && (
                            <div className="text-[10px] font-mono text-slate-500">
                              by {item.approved_by_email}
                            </div>
                          )}
                        </div>
                      ) : item.allocation_type === 'SAME_POD_REASSIGNMENT' ? (
                        <span className="text-[11px] text-slate-500 font-medium">
                          Auto-Authorized (Same Pod)
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

