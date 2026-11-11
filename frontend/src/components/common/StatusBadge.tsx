import React from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Sparkles,
  ArrowRightLeft,
  CalendarOff,
} from 'lucide-react';

interface StatusBadgeProps {
  type: 'roster' | 'conflict' | 'allocation' | 'leave' | 'generic';
  status: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, status, size = 'sm' }) => {
  const isSm = size === 'sm';
  const sizeClasses = isSm ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1';

  if (type === 'roster') {
    switch (status) {
      case 'PUBLISHED':
        return (
          <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/80 ${sizeClasses}`}>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            Published
          </span>
        );
      case 'VALIDATED':
        return (
          <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-blue-50 text-blue-700 border border-blue-200/80 ${sizeClasses}`}>
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            Validated
          </span>
        );
      case 'STALE':
        return (
          <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-amber-50 text-amber-700 border border-amber-200/80 ${sizeClasses}`}>
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            Stale (Config Drift)
          </span>
        );
      default:
        return (
          <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-slate-100 text-slate-700 border border-slate-200 ${sizeClasses}`}>
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            Draft
          </span>
        );
    }
  }

  if (type === 'conflict') {
    if (status === 'HARD_VIOLATION') {
      return (
        <span className={`inline-flex items-center gap-1.5 font-semibold rounded-full bg-rose-50 text-rose-700 border border-rose-200/80 ${sizeClasses}`}>
          <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
          Hard Violation
        </span>
      );
    }
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-amber-50 text-amber-700 border border-amber-200/80 ${sizeClasses}`}>
        <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
        Soft Warning
      </span>
    );
  }

  if (type === 'allocation') {
    switch (status) {
      case 'SAME_POD_REASSIGNMENT':
        return (
          <span className={`inline-flex items-center gap-1 font-medium rounded-md bg-sky-50 text-sky-700 border border-sky-200/80 ${sizeClasses}`}>
            <ArrowRightLeft className="w-3 h-3 text-sky-500" />
            Same-Pod Backup
          </span>
        );
      case 'CROSS_POD_REASSIGNMENT':
        return (
          <span className={`inline-flex items-center gap-1 font-semibold rounded-md bg-purple-50 text-purple-700 border border-purple-200/80 ${sizeClasses}`}>
            <ArrowRightLeft className="w-3 h-3 text-purple-600" />
            Cross-Pod (Approved)
          </span>
        );
      default:
        return (
          <span className={`inline-flex items-center font-medium rounded-md bg-slate-100 text-slate-700 border border-slate-200 ${sizeClasses}`}>
            Primary
          </span>
        );
    }
  }

  if (type === 'leave') {
    return (
      <span className={`inline-flex items-center gap-1 font-medium rounded-md bg-amber-50 text-amber-800 border border-amber-200 ${sizeClasses}`}>
        <CalendarOff className="w-3 h-3 text-amber-600" />
        {status.replace('_', ' ')}
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center font-medium rounded-md bg-slate-100 text-slate-700 border border-slate-200 ${sizeClasses}`}>
      {status}
    </span>
  );
};

