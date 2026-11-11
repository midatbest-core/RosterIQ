import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  badge?: {
    text: string;
    variant: 'emerald' | 'rose' | 'amber' | 'blue' | 'slate';
  };
  progress?: {
    percentage: number;
    color?: string;
  };
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  badge,
  progress,
}) => {
  const badgeStyles = {
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    rose: 'bg-rose-50 text-rose-700 border-rose-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    slate: 'bg-slate-100 text-slate-700 border-slate-200',
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs hover:border-slate-300 transition-all">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</p>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 tracking-tight">{value}</span>
            {badge && (
              <span
                className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${badgeStyles[badge.variant]}`}
              >
                {badge.text}
              </span>
            )}
          </div>
        </div>
        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-slate-600">
          {icon}
        </div>
      </div>

      {progress && (
        <div className="mt-3.5 space-y-1.5">
          <div className="flex justify-between text-xs text-slate-500">
            <span>Coverage</span>
            <span className="font-semibold text-slate-800">{Math.round(progress.percentage)}%</span>
          </div>
          <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                progress.color || (progress.percentage >= 95 ? 'bg-emerald-500' : progress.percentage >= 80 ? 'bg-amber-500' : 'bg-rose-500')
              }`}
              style={{ width: `${Math.min(100, Math.max(0, progress.percentage))}%` }}
            />
          </div>
        </div>
      )}

      {subtitle && <p className="text-xs text-slate-500 mt-2">{subtitle}</p>}
    </div>
  );
};

