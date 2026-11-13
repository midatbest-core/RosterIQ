import React from 'react';
import {
  Users,
  Network,
  Briefcase,
  Layers,
  UserCheck,
  Sparkles,
  Lock,
  GitBranch,
  Filter,
  Calendar,
  Download,
  FileSpreadsheet,
} from 'lucide-react';
import { RosterSummary, User } from '../../services/types';
import { StatusBadge } from '../common/StatusBadge';

export type RosterViewMode = 'company' | 'pod' | 'brand' | 'process' | 'employee';
export type TimeScope = 'month' | 'w1' | 'w2' | 'w3' | 'w4' | 'w5';

interface CalendarToolbarProps {
  viewMode: RosterViewMode;
  onViewModeChange: (mode: RosterViewMode) => void;
  timeScope: TimeScope;
  onTimeScopeChange: (scope: TimeScope) => void;
  currentRoster: RosterSummary | null;
  onPublish: () => void;
  onCreateChildVersion: () => void;
  onOpenGenerateModal: () => void;
  onOpenConflicts?: () => void;
  onExportCsv?: () => void;
  isExporting?: boolean;
  onExportGoogleSheets?: () => void;
  isExportingGoogle?: boolean;
  filterId: string;
  onFilterChange: (id: string) => void;
  filterOptions: { id: string; name: string }[];
  filterLabel: string;
  isPublishing?: boolean;
  currentUser?: User | null;
}

export const CalendarToolbar: React.FC<CalendarToolbarProps> = ({
  viewMode,
  onViewModeChange,
  timeScope,
  onTimeScopeChange,
  currentRoster,
  onPublish,
  onCreateChildVersion,
  onOpenGenerateModal,
  onOpenConflicts,
  onExportCsv,
  isExporting = false,
  onExportGoogleSheets,
  isExportingGoogle = false,
  filterId,
  onFilterChange,
  filterOptions,
  filterLabel,
  isPublishing = false,
  currentUser,
}) => {
  const isPodLead = currentUser?.role === 'POD_LEAD';

  const views: { id: RosterViewMode; label: string; icon: React.FC<{ className?: string }> }[] = isPodLead
    ? [
        { id: 'pod', label: 'Pod Team Allocation', icon: Network },
        { id: 'employee', label: 'My Personal Allocation', icon: UserCheck },
      ]
    : [
        { id: 'company', label: 'Company-Wide', icon: Users },
        { id: 'pod', label: 'Pod-Wise', icon: Network },
        { id: 'brand', label: 'Brand-Wise', icon: Briefcase },
        { id: 'process', label: 'Process-Wise', icon: Layers },
        { id: 'employee', label: 'Employee-Wise', icon: UserCheck },
      ];

  const isPublished = currentRoster?.status === 'PUBLISHED';
  const hasHardConflicts = (currentRoster?.hard_violations_count ?? 0) > 0;
  const isStale = currentRoster?.status === 'STALE';

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 p-3 shadow-2xs space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* 5 Viewing Mode Segmented Control */}
        <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200/60 overflow-x-auto">
          {views.map((v) => {
            const Icon = v.icon;
            const isActive = viewMode === v.id;
            return (
              <button
                key={v.id}
                onClick={() => onViewModeChange(v.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
                  isActive
                    ? 'bg-white text-indigo-700 shadow-2xs border border-slate-200/50'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-600' : 'text-slate-400'}`} />
                <span>{v.label}</span>
              </button>
            );
          })}
        </div>

        {/* Right Actions: Status & Management Actions */}
        <div className="flex items-center gap-2">
          {currentRoster && (
            <div className="flex items-center gap-2 mr-2">
              <StatusBadge type="roster" status={currentRoster.status} size="md" />
              <span className="text-xs font-mono font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                v{currentRoster.version}
              </span>
            </div>
          )}

          {currentRoster && onExportCsv && (
            <div className="flex items-center gap-1.5">
              <button
                onClick={onExportCsv}
                disabled={isExporting}
                title={`Export ${viewMode.toUpperCase()} schedule as CSV`}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold shadow-2xs transition-all cursor-pointer"
              >
                <Download className="w-3.5 h-3.5 text-slate-500" />
                <span>{isExporting ? 'Exporting...' : 'Export CSV'}</span>
              </button>

              {onExportGoogleSheets && (
                <button
                  onClick={onExportGoogleSheets}
                  disabled={isExportingGoogle}
                  title={`Export ${viewMode.toUpperCase()} schedule to Google Sheets`}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 rounded-lg text-xs font-semibold shadow-2xs transition-all cursor-pointer"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                  <span>{isExportingGoogle ? 'Exporting...' : 'Google Sheets'}</span>
                </button>
              )}
            </div>
          )}

          {/* If Published -> Offer Create Child Revision */}
          {/* Direct Auto-Resolver Quick Trigger from Calendar */}
          {hasHardConflicts && onOpenConflicts && (
            <button
              onClick={onOpenConflicts}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-300 rounded-lg text-xs font-bold transition-all shadow-2xs animate-pulse cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5 text-rose-600" />
              <span>Resolve {currentRoster?.hard_violations_count} Conflicts</span>
            </button>
          )}

          {!isPodLead && (
            <>
              {isPublished ? (
                <button
                  onClick={onCreateChildVersion}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                >
                  <GitBranch className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Create Child Revision</span>
                </button>
              ) : (
                /* If Draft/Validated -> Offer Publish Roster */
                currentRoster && (
                  <button
                    onClick={onPublish}
                    disabled={hasHardConflicts || isStale || isPublishing}
                    title={
                      hasHardConflicts
                        ? 'Resolve all hard conflicts before publishing'
                        : isStale
                        ? 'Roster is stale due to configuration drift. Regenerate before publishing.'
                        : 'Publish roster to lock changes'
                    }
                    className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition-all cursor-pointer ${
                      hasHardConflicts || isStale || isPublishing
                        ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
                        : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20'
                    }`}
                  >
                    <Lock className="w-3.5 h-3.5" />
                    <span>{isPublishing ? 'Publishing...' : 'Publish Roster'}</span>
                  </button>
                )
              )}

              <button
                onClick={onOpenGenerateModal}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-xs shadow-indigo-600/30 transition-all cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Generate Roster</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Time Scope Toggle: 30-Day Full Month vs Week-Wise */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2.5 border-t border-slate-100">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs font-semibold text-slate-500 mr-1 flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5 text-indigo-600" />
            <span>Time Window:</span>
          </span>
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200/60">
            <button
              onClick={() => onTimeScopeChange('month')}
              className={`px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                timeScope === 'month'
                  ? 'bg-indigo-600 text-white shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Month (30 Days Auto-Fit)
            </button>
            <button
              onClick={() => onTimeScopeChange('w1')}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                timeScope === 'w1'
                  ? 'bg-indigo-600 text-white shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Week 1 (1–7)
            </button>
            <button
              onClick={() => onTimeScopeChange('w2')}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                timeScope === 'w2'
                  ? 'bg-indigo-600 text-white shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Week 2 (8–14)
            </button>
            <button
              onClick={() => onTimeScopeChange('w3')}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                timeScope === 'w3'
                  ? 'bg-indigo-600 text-white shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Week 3 (15–21)
            </button>
            <button
              onClick={() => onTimeScopeChange('w4')}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                timeScope === 'w4'
                  ? 'bg-indigo-600 text-white shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Week 4 (22–28)
            </button>
            <button
              onClick={() => onTimeScopeChange('w5')}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                timeScope === 'w5'
                  ? 'bg-indigo-600 text-white shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Week 5 (29–30)
            </button>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-[11px] text-slate-500 font-medium">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-indigo-600" />
            <span>Scheduled Shift</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-rose-600 ring-2 ring-rose-300 animate-pulse" />
            <span className="font-bold text-rose-600">Conflict / Uncovered</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-slate-300" />
            <span>Weekly Off</span>
          </div>
        </div>
      </div>

      {/* Optional Contextual Filter Bar */}
      {filterOptions.length > 0 && (
        <div className="flex items-center gap-2 pt-2 border-t border-slate-100 text-xs text-slate-600">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-medium text-slate-500">Filter by {filterLabel}:</span>
          <select
            value={filterId}
            onChange={(e) => onFilterChange(e.target.value)}
            className="px-2.5 py-1 bg-slate-50 border border-slate-200 rounded-md text-xs font-medium text-slate-700 focus:outline-hidden focus:border-indigo-500 cursor-pointer"
          >
            <option value="">All {filterLabel}s</option>
            {filterOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.name}
              </option>
            ))}
          </select>
          {filterId && (
            <button
              onClick={() => onFilterChange('')}
              className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800"
            >
              Clear filter
            </button>
          )}
        </div>
      )}
    </div>
  );
};

