import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  RosterSummary,
  RosterGridView,
  GridRow,
  DayCell,
  AllocationCell,
  RosterConflict,
} from '../services/types';
import { CalendarToolbar, RosterViewMode, TimeScope } from '../components/roster/CalendarToolbar';
import { AllocationCard } from '../components/roster/AllocationCard';
import { AllocationDetailDrawer } from '../components/roster/AllocationDetailDrawer';
import { ReassignmentModal } from '../components/roster/ReassignmentModal';
import { StatusBadge } from '../components/common/StatusBadge';
import {
  Calendar,
  Clock,
  ShieldAlert,
  ArrowRightLeft,
  ChevronLeft,
  ChevronRight,
  Filter,
  Search,
} from 'lucide-react';

interface RosterCalendarScreenProps {
  rosters: RosterSummary[];
  selectedRosterId: string;
  onRefreshRosters: () => void;
  onOpenGenerateModal: () => void;
  searchQuery?: string;
}

export const RosterCalendarScreen: React.FC<RosterCalendarScreenProps> = ({
  rosters,
  selectedRosterId,
  onRefreshRosters,
  onOpenGenerateModal,
  searchQuery = '',
}) => {
  const [viewMode, setViewMode] = useState<RosterViewMode>('company');
  const [timeScope, setTimeScope] = useState<TimeScope>('month');
  const [gridData, setGridData] = useState<RosterGridView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterId, setFilterId] = useState<string>('');
  const [isPublishing, setIsPublishing] = useState(false);

  // Detail Drawer state
  const [selectedAllocation, setSelectedAllocation] = useState<AllocationCell | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Reassignment Modal state
  const [reassignSlot, setReassignSlot] = useState<{
    date: string;
    brand_process_id: string;
    brand_name: string;
    process_name: string;
    start_time: string;
    end_time: string;
    source_employee_id?: string;
    source_employee_name?: string;
  } | null>(null);
  const [isReassignOpen, setIsReassignOpen] = useState(false);

  const currentRoster = rosters.find((r) => r.id === selectedRosterId) || rosters[0];

  useEffect(() => {
    if (selectedRosterId) {
      loadGrid(selectedRosterId, viewMode, filterId);
    }
  }, [selectedRosterId, viewMode, filterId]);

  const loadGrid = async (rosterId: string, mode: RosterViewMode, fId?: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getRosterGrid(rosterId, mode, fId || undefined);
      setGridData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load roster calendar');
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!currentRoster) return;
    try {
      setIsPublishing(true);
      setError(null);
      await api.publishRoster(currentRoster.id);
      await onRefreshRosters();
      await loadGrid(currentRoster.id, viewMode, filterId);
    } catch (err: any) {
      setError(err.message || 'Publishing failed');
    } finally {
      setIsPublishing(false);
    }
  };

  const handleCreateChildVersion = async () => {
    if (!currentRoster) return;
    try {
      setLoading(true);
      setError(null);
      const child = await api.createChildVersion(currentRoster.id);
      await onRefreshRosters();
      await loadGrid(child.id, viewMode, filterId);
    } catch (err: any) {
      setError(err.message || 'Failed to create child version');
    } finally {
      setLoading(false);
    }
  };

  const handleCellClick = (alloc: AllocationCell, date: string) => {
    setSelectedAllocation(alloc);
    setSelectedDate(date);
    setIsDrawerOpen(true);
  };

  const handleOpenReassignFromCell = (
    date: string,
    brand_process_id: string,
    brand_name: string,
    process_name: string,
    start_time: string = '09:00:00',
    end_time: string = '18:00:00',
    source_emp_id?: string,
    source_emp_name?: string
  ) => {
    setReassignSlot({
      date,
      brand_process_id,
      brand_name,
      process_name,
      start_time,
      end_time,
      source_employee_id: source_emp_id,
      source_employee_name: source_emp_name,
    });
    setIsReassignOpen(true);
  };

  // Filter rows based on global search query
  const filteredRows = (gridData?.rows || []).filter((row) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      row.title.toLowerCase().includes(q) ||
      (row.subtitle && row.subtitle.toLowerCase().includes(q)) ||
      (row.group_name && row.group_name.toLowerCase().includes(q))
    );
  });

  // Extract filter options dynamically from rows
  const filterOptions = Array.from(
    new Map(
      (gridData?.rows || [])
        .filter((r) => r.group_id && r.group_name)
        .map((r) => [r.group_id as string, { id: r.group_id as string, name: r.group_name as string }])
    ).values()
  );

  const filterLabel =
    viewMode === 'pod' || viewMode === 'company' || viewMode === 'employee'
      ? 'Pod'
      : viewMode === 'brand'
      ? 'Brand'
      : 'Process';

  const allDates = gridData?.dates || [];
  const conflicts = gridData?.summary_conflicts || [];

  const dates = React.useMemo(() => {
    if (timeScope === 'w1') return allDates.slice(0, 7);
    if (timeScope === 'w2') return allDates.slice(7, 14);
    if (timeScope === 'w3') return allDates.slice(14, 21);
    if (timeScope === 'w4') return allDates.slice(21, 28);
    if (timeScope === 'w5') return allDates.slice(28, 30);
    return allDates;
  }, [allDates, timeScope]);

  const isMonthMode = timeScope === 'month';

  return (
    <div className="space-y-4">
      {/* Calendar Toolbar */}
      <CalendarToolbar
        viewMode={viewMode}
        onViewModeChange={(mode) => {
          setViewMode(mode);
          setFilterId('');
        }}
        timeScope={timeScope}
        onTimeScopeChange={setTimeScope}
        currentRoster={currentRoster}
        onPublish={handlePublish}
        onCreateChildVersion={handleCreateChildVersion}
        onOpenGenerateModal={onOpenGenerateModal}
        filterId={filterId}
        onFilterChange={setFilterId}
        filterOptions={filterOptions}
        filterLabel={filterLabel}
        isPublishing={isPublishing}
      />

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-xs font-semibold text-rose-800 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Calendar Grid Canvas */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden flex flex-col">
        {loading ? (
          <div className="py-24 text-center space-y-2">
            <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs font-semibold text-slate-700">Loading {viewMode} schedule perspective...</p>
          </div>
        ) : filteredRows.length === 0 ? (
          <div className="py-20 text-center space-y-2">
            <Calendar className="w-8 h-8 text-slate-400 mx-auto" />
            <p className="text-xs font-semibold text-slate-800">No schedules found for current filters</p>
            <p className="text-[11px] text-slate-500">Try adjusting your search query or generate a roster.</p>
          </div>
        ) : (
          <div className="overflow-x-auto max-h-[75vh]">
            <table className="w-full border-collapse text-left text-xs">
              {/* Sticky Calendar Date Header */}
              <thead className="sticky top-0 z-20 bg-slate-50/95 backdrop-blur-xs border-b border-slate-200 text-slate-600 font-semibold select-none">
                <tr>
                  <th
                    className={`sticky left-0 z-30 bg-slate-50/95 py-2.5 border-r border-slate-200 shadow-xs ${
                      isMonthMode
                        ? 'px-2.5 w-[150px] min-w-[150px] max-w-[150px]'
                        : 'px-4 min-w-[220px] max-w-[260px]'
                    }`}
                  >
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      {viewMode === 'brand' || viewMode === 'process' ? 'Process / Brand' : 'Employee / Pod'}
                    </span>
                  </th>
                  {dates.map((dateStr) => {
                    const dateObj = new Date(dateStr);
                    const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'short' });
                    const dayNum = dateObj.getDate();
                    const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6;

                    return (
                      <th
                        key={dateStr}
                        className={`py-2 text-center border-r border-slate-200/80 last:border-r-0 select-none ${
                          isMonthMode
                            ? 'px-0.5 w-[32px] min-w-[28px] max-w-[36px]'
                            : 'px-2 min-w-[130px]'
                        } ${isWeekend ? 'bg-slate-100/70 text-slate-900' : 'text-slate-700'}`}
                      >
                        <div
                          className={`uppercase font-bold text-slate-400 ${
                            isMonthMode ? 'text-[8px]' : 'text-[10px]'
                          }`}
                        >
                          {dayName.slice(0, 2)}
                        </div>
                        <div
                          className={`font-extrabold text-slate-900 ${
                            isMonthMode ? 'text-[11px] mt-0' : 'text-xs mt-0.5'
                          }`}
                        >
                          {dayNum}
                        </div>
                      </th>
                    );
                  })}
                </tr>
              </thead>

              {/* Grid Body */}
              <tbody className="divide-y divide-slate-100">
                {filteredRows.map((row) => (
                  <tr key={row.row_id} className="hover:bg-slate-50/40 transition-colors">
                    {/* Sticky Row Title Cell */}
                    <td
                      className={`sticky left-0 z-10 bg-white border-r border-slate-200/80 shadow-xs align-top ${
                        isMonthMode
                          ? 'px-2.5 py-2 w-[150px] min-w-[150px] max-w-[150px]'
                          : 'px-4 py-3 min-w-[220px]'
                      }`}
                    >
                      <div className="space-y-0.5">
                        <span className="font-bold text-slate-900 block truncate text-xs" title={row.title}>
                          {row.title}
                        </span>
                        {row.subtitle && (
                          <span className="text-[10px] text-slate-500 block truncate" title={row.subtitle}>
                            {row.subtitle}
                          </span>
                        )}
                        {row.group_name && (
                          <span className="inline-block mt-0.5 text-[9px] font-semibold px-1 rounded-xs bg-slate-100 text-slate-600 border border-slate-200 truncate max-w-full">
                            {row.group_name}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Day Cells */}
                    {dates.map((dateStr) => {
                      const cell = row.days[dateStr];
                      const dateObj = new Date(dateStr);
                      const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6;
                      const hasAllocs = cell && cell.allocations && cell.allocations.length > 0;
                      const cellConflicts = conflicts.filter(
                        (c) =>
                          c.date === dateStr &&
                          (c.employee_id === row.row_id ||
                            c.brand_process_id === row.row_id ||
                            (row.row_type === 'BRAND_PROCESS' && c.brand_process_id === row.row_id))
                      );
                      const hasConflict = cellConflicts.length > 0;
                      const hasHardConflict = cellConflicts.some((c) => c.severity === 'HARD_VIOLATION');

                      if (isMonthMode) {
                        /* 30-Day Auto-Fit Month View Mode */
                        if (hasConflict) {
                          return (
                            <td
                              key={dateStr}
                              className="p-0.5 border-r border-rose-300 last:border-r-0 align-middle bg-rose-100 ring-1 ring-rose-400"
                            >
                              <button
                                onClick={() => {
                                  const bpId = cellConflicts[0]?.brand_process_id || row.row_id;
                                  handleOpenReassignFromCell(
                                    dateStr,
                                    bpId,
                                    row.title,
                                    'Conflict Resolution',
                                    '09:00:00',
                                    '18:00:00',
                                    row.row_type === 'EMPLOYEE' ? row.row_id : undefined,
                                    row.row_type === 'EMPLOYEE' ? row.title : undefined
                                  );
                                }}
                                className="w-full h-7 bg-rose-600 hover:bg-rose-700 text-white font-black text-[11px] rounded flex items-center justify-center shadow-xs cursor-pointer animate-pulse transition-all"
                                title={`Conflict: ${cellConflicts[0]?.description || 'Uncovered demand or constraint violation'}`}
                              >
                                !
                              </button>
                            </td>
                          );
                        }

                        if (hasAllocs) {
                          return (
                            <td
                              key={dateStr}
                              className="p-0.5 border-r border-slate-200/60 last:border-r-0 align-middle"
                            >
                              <div className="space-y-0.5">
                                {cell.allocations.map((a) => (
                                  <button
                                    key={a.allocation_id}
                                    onClick={() => handleCellClick(a, dateStr)}
                                    className="w-full py-1 rounded text-[9px] font-extrabold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200/80 block text-center truncate cursor-pointer transition-colors shadow-2xs"
                                    title={`${a.employee_name} · ${a.brand_name} (${a.process_name}) [${a.start_time} - ${a.end_time}]`}
                                  >
                                    {a.brand_name.slice(0, 3).toUpperCase()}
                                  </button>
                                ))}
                              </div>
                            </td>
                          );
                        }

                        return (
                          <td
                            key={dateStr}
                            className={`p-0.5 border-r border-slate-200/60 last:border-r-0 align-middle text-center ${
                              isWeekend ? 'bg-slate-50 text-slate-300' : 'text-slate-200'
                            }`}
                          >
                            <span className="text-[9px] font-mono select-none">·</span>
                          </td>
                        );
                      }

                      /* Week View Mode (Expanded Detail Cards) */
                      return (
                        <td
                          key={dateStr}
                          className={`p-1.5 border-r border-slate-200/60 last:border-r-0 align-top ${
                            hasConflict
                              ? 'bg-rose-50/70 border-rose-300 ring-1 ring-rose-400'
                              : isWeekend
                              ? 'bg-slate-50/40'
                              : ''
                          }`}
                        >
                          {hasConflict && (
                            <div className="mb-1.5 px-2 py-1 rounded bg-rose-100 border border-rose-300 text-rose-800 text-[10px] font-bold flex items-center justify-between shadow-2xs">
                              <span className="flex items-center gap-1">
                                <ShieldAlert className="w-3 h-3 text-rose-600 animate-pulse" />
                                <span>CONFLICT</span>
                              </span>
                              <button
                                onClick={() => {
                                  const bpId = cellConflicts[0]?.brand_process_id || row.row_id;
                                  handleOpenReassignFromCell(
                                    dateStr,
                                    bpId,
                                    row.title,
                                    'Conflict Resolution',
                                    '09:00:00',
                                    '18:00:00',
                                    row.row_type === 'EMPLOYEE' ? row.row_id : undefined,
                                    row.row_type === 'EMPLOYEE' ? row.title : undefined
                                  );
                                }}
                                className="underline text-rose-700 hover:text-rose-900 cursor-pointer text-[9px]"
                              >
                                Resolve
                              </button>
                            </div>
                          )}

                          {hasAllocs ? (
                            <div className="space-y-1.5">
                              {cell.allocations.map((a) => (
                                <AllocationCard
                                  key={a.allocation_id}
                                  allocation={a}
                                  viewMode={viewMode}
                                  onClick={() => handleCellClick(a, dateStr)}
                                  hasConflict={hasHardConflict}
                                />
                              ))}
                            </div>
                          ) : hasConflict ? (
                            <div className="h-16 rounded-lg border-2 border-rose-400 bg-rose-100/60 flex flex-col items-center justify-center p-1.5 text-center shadow-xs space-y-1">
                              <span className="text-[10px] font-extrabold text-rose-800 flex items-center gap-1">
                                <ShieldAlert className="w-3.5 h-3.5 text-rose-600 animate-pulse" />
                                UNCOVERED GAP
                              </span>
                              <button
                                onClick={() => {
                                  const bpId = cellConflicts[0]?.brand_process_id || row.row_id;
                                  handleOpenReassignFromCell(
                                    dateStr,
                                    bpId,
                                    row.title,
                                    'Uncovered Demand Gap',
                                    '09:00:00',
                                    '18:00:00',
                                    row.row_type === 'EMPLOYEE' ? row.row_id : undefined,
                                    row.row_type === 'EMPLOYEE' ? row.title : undefined
                                  );
                                }}
                                className="text-[10px] font-bold text-white bg-rose-600 hover:bg-rose-700 px-2 py-0.5 rounded shadow-xs cursor-pointer transition-colors"
                                title={cellConflicts[0].description}
                              >
                                Reassign Now
                              </button>
                            </div>
                          ) : (
                            <div className="h-14 rounded-md border border-dashed border-slate-200/80 bg-slate-50/20 flex flex-col items-center justify-center p-1 text-center group hover:border-slate-300 transition-colors">
                              {isWeekend ? (
                                <span className="text-[10px] font-mono text-slate-400">WEEKLY OFF</span>
                              ) : (
                                <span className="text-[10px] font-mono text-slate-300">—</span>
                              )}
                            </div>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Allocation Detail Slide-Over Drawer */}
      <AllocationDetailDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        allocation={selectedAllocation}
        date={selectedDate}
        conflicts={conflicts}
        onOpenReassign={() => {
          if (selectedAllocation) {
            handleOpenReassignFromCell(
              selectedDate,
              selectedAllocation.brand_process_id,
              selectedAllocation.brand_name,
              selectedAllocation.process_name,
              selectedAllocation.start_time + ':00',
              selectedAllocation.end_time + ':00',
              selectedAllocation.employee_id,
              selectedAllocation.employee_name
            );
          }
        }}
        isRosterPublished={currentRoster?.status === 'PUBLISHED'}
      />

      {/* Reassignment Modal */}
      <ReassignmentModal
        isOpen={isReassignOpen}
        onClose={() => setIsReassignOpen(false)}
        rosterId={currentRoster?.id || ''}
        slot={reassignSlot}
        onReassigned={async () => {
          if (currentRoster) {
            await onRefreshRosters();
            await loadGrid(currentRoster.id, viewMode, filterId);
          }
        }}
      />
    </div>
  );
};

