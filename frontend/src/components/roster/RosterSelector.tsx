import React, { useState, useRef, useEffect } from 'react';
import { RosterSummary } from '../../services/types';
import {
  Calendar,
  ChevronDown,
  Check,
  Sparkles,
  Layers,
  Clock,
  Plus,
} from 'lucide-react';

export const cleanRosterName = (name: string): string => {
  return name.replace(/(\s*\(v\d+\))+/g, '').trim();
};

const monthNames = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

interface RosterSelectorProps {
  rosters: RosterSummary[];
  selectedRosterId: string;
  onSelectRosterId: (id: string) => void;
  onOpenGenerateRoster?: () => void;
  compact?: boolean;
}

export const RosterSelector: React.FC<RosterSelectorProps> = ({
  rosters,
  selectedRosterId,
  onSelectRosterId,
  onOpenGenerateRoster,
  compact = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const currentRoster = rosters.find((r) => r.id === selectedRosterId) || rosters[0];

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  if (!rosters || rosters.length === 0) {
    return null;
  }

  // Group rosters by Month/Year (e.g., "December 2026", "November 2026")
  const grouped: Record<string, RosterSummary[]> = {};
  for (const r of rosters) {
    const mName = monthNames[r.month - 1] || `Month ${r.month}`;
    const groupKey = `${mName} ${r.year}`;
    if (!grouped[groupKey]) {
      grouped[groupKey] = [];
    }
    grouped[groupKey].push(r);
  }

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'PUBLISHED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
            <span>Published</span>
          </span>
        );
      case 'VALIDATED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
            <span>Validated</span>
          </span>
        );
      case 'DRAFT':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0" />
            <span>Draft</span>
          </span>
        );
      case 'STALE':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-50 text-amber-700 border border-amber-200">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
            <span>Stale</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      {/* Visual Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200/90 hover:border-slate-300 rounded-xl text-xs font-semibold text-slate-800 shadow-2xs hover:bg-slate-50/80 transition-all cursor-pointer group"
        title="Switch Production Roster"
      >
        <div className="p-1 rounded-lg bg-indigo-50 text-indigo-600 group-hover:bg-indigo-100 transition-colors shrink-0">
          <Calendar className="w-3.5 h-3.5" />
        </div>

        <div className="flex items-center gap-2 max-w-[260px] truncate text-left">
          <span className="truncate font-bold text-slate-900">
            {currentRoster ? cleanRosterName(currentRoster.name) : 'Select Roster'}
          </span>
          {currentRoster && (
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 font-bold shrink-0">
              v{currentRoster.version}
            </span>
          )}
        </div>

        {currentRoster && !compact && renderStatusBadge(currentRoster.status)}

        <ChevronDown
          className={`w-3.5 h-3.5 text-slate-400 group-hover:text-slate-600 transition-transform duration-200 shrink-0 ml-0.5 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Visual Dropdown Popover */}
      {isOpen && (
        <div className="absolute left-0 mt-2 w-80 sm:w-96 bg-white border border-slate-200 rounded-2xl shadow-2xl z-[99999] overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
          {/* Header */}
          <div className="px-4 py-3 bg-slate-50/90 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
                <Layers className="w-3.5 h-3.5" />
              </div>
              <div>
                <span className="text-xs font-bold text-slate-900 block leading-tight">
                  Production Schedules
                </span>
                <span className="text-[10px] text-slate-500 block leading-tight">
                  Active planning & published versions
                </span>
              </div>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">
              {rosters.length} Version{rosters.length !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Grouped Rosters List */}
          <div className="max-h-80 overflow-y-auto divide-y divide-slate-100 p-2 space-y-2">
            {Object.entries(grouped).map(([groupTitle, groupRosters]) => (
              <div key={groupTitle} className="pt-1.5 first:pt-0">
                <div className="px-2 pb-1.5 flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  <span>{groupTitle}</span>
                  <span className="text-slate-300 font-normal">
                    {groupRosters.length} run{groupRosters.length !== 1 ? 's' : ''}
                  </span>
                </div>

                <div className="space-y-1">
                  {groupRosters.map((r) => {
                    const isSelected = r.id === selectedRosterId;
                    return (
                      <button
                        key={r.id}
                        type="button"
                        onClick={() => {
                          onSelectRosterId(r.id);
                          setIsOpen(false);
                        }}
                        className={`w-full flex items-center justify-between gap-3 p-2.5 rounded-xl text-left transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-indigo-50/90 border border-indigo-200 text-indigo-950 shadow-2xs'
                            : 'hover:bg-slate-50 border border-transparent text-slate-800'
                        }`}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className="text-xs font-bold truncate text-slate-900">
                              {cleanRosterName(r.name)}
                            </span>
                            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-200/80 text-slate-700 font-bold shrink-0">
                              v{r.version}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-[10px] text-slate-500">
                            <span className="flex items-center gap-1 font-medium">
                              <Clock className="w-3 h-3 text-slate-400" />
                              {monthNames[r.month - 1]} {r.year}
                            </span>
                            <span className="text-slate-300">&bull;</span>
                            {renderStatusBadge(r.status)}
                          </div>
                        </div>

                        {isSelected && (
                          <div className="p-1 rounded-full bg-indigo-600 text-white shrink-0">
                            <Check className="w-3 h-3 stroke-[2.5]" />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Footer with optional Generate action */}
          {onOpenGenerateRoster && (
            <div className="p-2 bg-slate-50/70 border-t border-slate-100 flex items-center justify-end">
              <button
                type="button"
                onClick={() => {
                  setIsOpen(false);
                  onOpenGenerateRoster();
                }}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 font-semibold rounded-lg text-xs transition-colors cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5 text-indigo-600" />
                <span>Generate New Roster</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
