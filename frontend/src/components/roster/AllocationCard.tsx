import React from 'react';
import { AllocationCell } from '../../services/types';
import { Clock, ArrowRightLeft, ShieldAlert, CheckCircle2 } from 'lucide-react';

interface AllocationCardProps {
  allocation: AllocationCell;
  viewMode: 'company' | 'pod' | 'brand' | 'process' | 'employee';
  onClick?: () => void;
  hasConflict?: boolean;
}

export const AllocationCard: React.FC<AllocationCardProps> = ({
  allocation,
  viewMode,
  onClick,
  hasConflict = false,
}) => {
  const isCrossPod = allocation.allocation_type === 'CROSS_POD_REASSIGNMENT';
  const isSamePod = allocation.allocation_type === 'SAME_POD_REASSIGNMENT';

  // Card theme based on allocation type & conflict
  let borderClass = 'border-slate-200/90 border-l-3 border-l-indigo-600 bg-white hover:border-slate-300';
  let badgeClass = 'bg-slate-100 text-slate-700';

  if (hasConflict) {
    borderClass = 'border-rose-300 border-l-3 border-l-rose-600 bg-rose-50/40 hover:bg-rose-50/60';
  } else if (isCrossPod) {
    borderClass = 'border-purple-200 border-l-3 border-l-purple-600 bg-purple-50/40 hover:bg-purple-50/70';
    badgeClass = 'bg-purple-100 text-purple-800';
  } else if (isSamePod) {
    borderClass = 'border-sky-200 border-l-3 border-l-sky-600 bg-sky-50/40 hover:bg-sky-50/70';
    badgeClass = 'bg-sky-100 text-sky-800';
  }

  // Display text depending on viewing perspective
  const primaryLabel =
    viewMode === 'brand' || viewMode === 'process'
      ? allocation.employee_name
      : `${allocation.brand_name} · ${allocation.process_name}`;

  return (
    <div
      onClick={onClick}
      className={`p-1.5 rounded-md border text-[11px] transition-all cursor-pointer shadow-2xs space-y-1 ${borderClass}`}
    >
      <div className="flex items-center justify-between gap-1 leading-tight">
        <span className="font-semibold text-slate-900 truncate" title={primaryLabel}>
          {primaryLabel}
        </span>
        {hasConflict && <ShieldAlert className="w-3 h-3 text-rose-600 shrink-0" />}
      </div>

      <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
        <span className="flex items-center gap-1">
          <Clock className="w-2.8 h-2.8 text-slate-400" />
          {allocation.start_time}-{allocation.end_time}
        </span>
        {(isSamePod || isCrossPod) && (
          <span
            className={`px-1 py-0.2 rounded-xs font-sans font-semibold text-[9px] ${badgeClass}`}
            title={isCrossPod ? 'Cross-Pod Backup (Ops Approved)' : 'Same-Pod Backup'}
          >
            {isCrossPod ? 'X-Pod' : 'Backup'}
          </span>
        )}
      </div>
    </div>
  );
};

