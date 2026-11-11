import React from 'react';
import { DetailDrawer } from '../layout/DetailDrawer';
import { AllocationCell, RosterConflict } from '../../services/types';
import { StatusBadge } from '../common/StatusBadge';
import {
  Calendar,
  Clock,
  Briefcase,
  Layers,
  User,
  ShieldCheck,
  ShieldAlert,
  ArrowRightLeft,
  CheckCircle2,
} from 'lucide-react';

interface AllocationDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  allocation: AllocationCell | null;
  date: string;
  conflicts: RosterConflict[];
  onOpenReassign: () => void;
  isRosterPublished?: boolean;
}

export const AllocationDetailDrawer: React.FC<AllocationDetailDrawerProps> = ({
  isOpen,
  onClose,
  allocation,
  date,
  conflicts,
  onOpenReassign,
  isRosterPublished = false,
}) => {
  if (!allocation) return null;

  const slotConflicts = conflicts.filter(
    (c) =>
      c.date === date &&
      (c.brand_process_id === allocation.brand_process_id || c.employee_id === allocation.employee_id)
  );

  return (
    <DetailDrawer
      isOpen={isOpen}
      onClose={onClose}
      title="Allocation & Shift Inspector"
      subtitle={`Calendar Date: ${date}`}
      width="lg"
    >
      <div className="space-y-6">
        {/* Status & Allocation Type Banner */}
        <div className="flex items-center justify-between p-3.5 bg-slate-50 border border-slate-200/80 rounded-xl">
          <div className="space-y-0.5">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              Allocation Model
            </span>
            <div>
              <StatusBadge type="allocation" status={allocation.allocation_type} size="md" />
            </div>
          </div>
          {allocation.is_cross_pod_approved && (
            <div className="flex items-center gap-1.5 text-xs font-semibold text-purple-700 bg-purple-50 px-2.5 py-1 rounded-lg border border-purple-200">
              <ShieldCheck className="w-4 h-4 text-purple-600" />
              <span>Ops Manager Approved</span>
            </div>
          )}
        </div>

        {/* Shift Interval Details */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-600" />
            Shift Interval
          </h4>
          <div className="grid grid-cols-2 gap-3 bg-white p-4 border border-slate-200/80 rounded-xl text-xs">
            <div>
              <span className="text-slate-500">Start Time:</span>
              <p className="font-mono font-bold text-slate-800 text-sm mt-0.5">
                {allocation.start_time}
              </p>
            </div>
            <div>
              <span className="text-slate-500">End Time:</span>
              <p className="font-mono font-bold text-slate-800 text-sm mt-0.5">
                {allocation.end_time}
              </p>
            </div>
          </div>
        </div>

        {/* Assigned Workforce & Brand Details */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <User className="w-4 h-4 text-indigo-600" />
            Assignment Context
          </h4>
          <div className="space-y-2.5 bg-white p-4 border border-slate-200/80 rounded-xl text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <span className="text-slate-500">Assigned Employee:</span>
              <span className="font-semibold text-slate-900">{allocation.employee_name}</span>
            </div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <span className="text-slate-500">Brand:</span>
              <span className="font-semibold text-slate-900">{allocation.brand_name}</span>
            </div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <span className="text-slate-500">Operational Process:</span>
              <span className="font-semibold text-indigo-600">{allocation.process_name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Interval Coverage:</span>
              <span className="text-emerald-700 font-medium inline-flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> 100% Covered
              </span>
            </div>
          </div>
        </div>

        {/* Active Conflict Warnings if any */}
        {slotConflicts.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-rose-700 uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600" />
              Detected Conflict Warnings ({slotConflicts.length})
            </h4>
            <div className="space-y-2">
              {slotConflicts.map((c) => (
                <div
                  key={c.id}
                  className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-rose-800">{c.conflict_type}</span>
                    <StatusBadge type="conflict" status={c.severity} />
                  </div>
                  <p className="text-rose-700 leading-relaxed">{c.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Manager Actions */}
        <div className="pt-4 border-t border-slate-200 space-y-3">
          <button
            onClick={() => {
              onClose();
              onOpenReassign();
            }}
            disabled={isRosterPublished}
            className={`w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-semibold shadow-xs transition-all cursor-pointer ${
              isRosterPublished
                ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30'
            }`}
          >
            <ArrowRightLeft className="w-4 h-4" />
            <span>Find Backup Candidate & Reassign</span>
          </button>
          {isRosterPublished && (
            <p className="text-[11px] text-center text-slate-500 italic">
              Published rosters are immutable. Create a child revision to reassign.
            </p>
          )}
        </div>
      </div>
    </DetailDrawer>
  );
};

