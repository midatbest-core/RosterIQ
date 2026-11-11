import React from 'react';
import { RosterSummary } from '../services/types';
import { StatusBadge } from '../components/common/StatusBadge';
import {
  History,
  GitBranch,
  Lock,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Calendar,
  Layers,
  Hash,
} from 'lucide-react';

interface AuditHistoryScreenProps {
  rosters: RosterSummary[];
  onSelectRosterId: (id: string) => void;
  onCreateChildVersion: (rosterId: string) => void;
  onPublishRoster: (rosterId: string) => void;
}

export const AuditHistoryScreen: React.FC<AuditHistoryScreenProps> = ({
  rosters,
  onSelectRosterId,
  onCreateChildVersion,
  onPublishRoster,
}) => {
  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-2xs">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-indigo-600" />
          <h2 className="text-base font-bold text-slate-900">Roster Versioning & Audit History</h2>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Complete lineage of deterministic monthly rosters, cryptographic configuration hashes, and immutable published baselines.
        </p>
      </div>

      {/* Version Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="px-4 py-3">Roster Name</th>
                <th className="px-4 py-3">Version</th>
                <th className="px-4 py-3">Period</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Shifts / Allocs</th>
                <th className="px-4 py-3">Conflicts</th>
                <th className="px-4 py-3">Config Hash</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rosters.map((r) => {
                const isPublished = r.status === 'PUBLISHED';
                return (
                  <tr key={r.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-3.5 h-3.5 text-indigo-600" />
                        <span>{r.name}</span>
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        Created by {r.created_by}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono font-bold bg-slate-100 px-2 py-0.5 rounded text-slate-700">
                        v{r.version}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-700">
                      {String(r.month).padStart(2, '0')} / {r.year}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge type="roster" status={r.status} />
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-700">
                      {r.total_shifts} shifts · {r.total_allocations} allocs
                    </td>
                    <td className="px-4 py-3">
                      {r.hard_violations_count > 0 ? (
                        <span className="text-rose-600 font-bold">
                          {r.hard_violations_count} Hard Conflicts
                        </span>
                      ) : (
                        <span className="text-emerald-700 font-medium inline-flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Clean
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-[10px] text-slate-400 truncate max-w-[120px]" title={r.config_hash || ''}>
                      {r.config_hash ? r.config_hash.slice(0, 10) + '...' : '—'}
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button
                        onClick={() => onSelectRosterId(r.id)}
                        className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold cursor-pointer"
                      >
                        Inspect &rarr;
                      </button>
                      {isPublished && (
                        <button
                          onClick={() => onCreateChildVersion(r.id)}
                          className="text-xs text-purple-700 hover:text-purple-900 font-semibold cursor-pointer"
                        >
                          Branch &rarr;
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
