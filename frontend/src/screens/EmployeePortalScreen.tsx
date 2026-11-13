import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  EmployeeProfile,
  EmployeeTaskItem,
  EmployeeAvailabilityRequest,
  EmployeeUnavailability,
} from '../services/types';
import {
  User as UserIcon,
  Calendar as CalendarIcon,
  Clock,
  Briefcase,
  CheckCircle2,
  XCircle,
  AlertCircle,
  FileText,
  RefreshCw,
  Plus,
  Send,
  HelpCircle,
  Layers,
  Download,
  FileSpreadsheet,
  ChevronLeft,
  ChevronRight,
  CalendarOff,
  Sun,
  MapPin,
  CalendarCheck,
  CalendarDays,
} from 'lucide-react';

export const EmployeePortalScreen: React.FC = () => {
  const [profile, setProfile] = useState<EmployeeProfile | null>(null);
  const [tasks, setTasks] = useState<EmployeeTaskItem[]>([]);
  const [requests, setRequests] = useState<EmployeeAvailabilityRequest[]>([]);
  const [unavailabilities, setUnavailabilities] = useState<EmployeeUnavailability[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportingGoogle, setExportingGoogle] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // View Mode: 'calendar' (monthly grid) vs 'day' (day-by-day sequence)
  const [viewMode, setViewMode] = useState<'calendar' | 'day'>('calendar');

  // Compute Today's ISO String (YYYY-MM-DD)
  const now = new Date();
  const todayIso = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(
    now.getDate()
  ).padStart(2, '0')}`;

  // Calendar Month & Selected Date
  const [currentYear, setCurrentYear] = useState<number>(now.getFullYear());
  const [currentMonth, setCurrentMonth] = useState<number>(now.getMonth() + 1); // 1-12
  const [selectedDate, setSelectedDate] = useState<string>(todayIso);

  // Leave Request Modal state
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [requestType, setRequestType] = useState<string>('LEAVE');
  const [reasonType, setReasonType] = useState<string>('PLANNED_LEAVE');
  const [startDate, setStartDate] = useState<string>(todayIso);
  const [endDate, setEndDate] = useState<string>(todayIso);
  const [notes, setNotes] = useState<string>('');

  useEffect(() => {
    loadData();
  }, [currentMonth, currentYear]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [profData, tasksData, reqsData] = await Promise.all([
        api.getEmployeeProfile(),
        api.getEmployeeTasks(currentMonth, currentYear),
        api.getEmployeeRequests(),
      ]);
      setProfile(profData);
      setTasks(tasksData);
      setRequests(reqsData);

      if (profData?.employee_id) {
        const unavailData = await api.getEmployeeUnavailability(profData.employee_id).catch(() => []);
        setUnavailabilities(unavailData);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load employee portal data');
    } finally {
      setLoading(false);
    }
  };

  const handleExportMySchedule = async () => {
    if (!tasks || tasks.length === 0 || !profile?.employee_id) return;
    try {
      setExporting(true);
      setError(null);
      await api.exportRosterCsv(tasks[0].roster_id, 'employee', profile.employee_id);
    } catch (err: any) {
      setError(err.message || 'Failed to export schedule');
    } finally {
      setExporting(false);
    }
  };

  const handleExportGoogleSheets = async () => {
    if (!tasks || tasks.length === 0 || !profile?.employee_id) return;
    try {
      setExportingGoogle(true);
      setError(null);
      const res = await api.exportEmployeeGoogleSheets(tasks[0].roster_id);
      if (res && res.spreadsheet_url) {
        window.open(res.spreadsheet_url, '_blank', 'noopener,noreferrer');
      }
    } catch (err: any) {
      setError(err.message || 'Google Sheets export failed. Direct CSV export is available.');
    } finally {
      setExportingGoogle(false);
    }
  };

  const handleSubmitRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setError(null);
      await api.submitEmployeeRequest({
        request_type: requestType,
        reason_type: reasonType,
        start_date: startDate,
        end_date: endDate,
        notes: notes,
      });

      setSuccess('Leave / Availability adjustment request submitted to Operations Managers.');
      setShowRequestModal(false);
      setNotes('');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to submit request');
    } finally {
      setSubmitting(false);
    }
  };

  // Helper: check if date has approved leave
  const getLeaveForDate = (dateStr: string) => {
    // 1. Direct unavailabilities
    const unavail = unavailabilities.find(
      (u) => u.date === dateStr && u.is_approved !== false
    );
    if (unavail) {
      return {
        isLeave: true,
        reason: unavail.reason_type.replace(/_/g, ' '),
        notes: unavail.notes,
      };
    }
    // 2. Approved availability requests
    const req = requests.find((r) => {
      if (!['APPROVED', 'ROSTER_PENDING', 'IMPLEMENTED'].includes(r.status)) return false;
      return r.start_date <= dateStr && dateStr <= r.end_date;
    });
    if (req) {
      return {
        isLeave: true,
        reason: req.reason_type.replace(/_/g, ' '),
        notes: req.notes,
      };
    }
    return { isLeave: false };
  };

  // Helper: check shift for date (omitted if approved leave)
  const getShiftsForDate = (dateStr: string) => {
    const leave = getLeaveForDate(dateStr);
    if (leave.isLeave) {
      return [];
    }
    return tasks.filter((t) => t.date === dateStr);
  };

  const getShiftForDate = (dateStr: string) => {
    const list = getShiftsForDate(dateStr);
    return list.length > 0 ? list[0] : null;
  };

  // Helper: get 7 days of the week containing the base date (Mon - Sun)
  const getWeekDays = (baseDateStr: string) => {
    const d = new Date(baseDateStr + 'T00:00:00');
    const dayOfWeek = d.getDay(); // 0 is Sunday, 1 is Monday...
    const distanceToMonday = (dayOfWeek + 6) % 7;
    const monday = new Date(d);
    monday.setDate(d.getDate() - distanceToMonday);

    const days = [];
    for (let i = 0; i < 7; i++) {
      const cur = new Date(monday);
      cur.setDate(monday.getDate() + i);
      const y = cur.getFullYear();
      const m = String(cur.getMonth() + 1).padStart(2, '0');
      const dayNum = String(cur.getDate()).padStart(2, '0');
      days.push(`${y}-${m}-${dayNum}`);
    }
    return days;
  };

  // Month Navigation
  const handlePrevMonth = () => {
    if (currentMonth === 1) {
      setCurrentMonth(12);
      setCurrentYear((y) => y - 1);
    } else {
      setCurrentMonth((m) => m - 1);
    }
  };

  const handleNextMonth = () => {
    if (currentMonth === 12) {
      setCurrentMonth(1);
      setCurrentYear((y) => y + 1);
    } else {
      setCurrentMonth((m) => m + 1);
    }
  };

  const handleGoToToday = () => {
    const t = new Date();
    setCurrentYear(t.getFullYear());
    setCurrentMonth(t.getMonth() + 1);
    setSelectedDate(todayIso);
  };

  // Day Stepper for Day-Wise view
  const handleStepDay = (delta: number) => {
    const [y, m, d] = selectedDate.split('-').map(Number);
    const dateObj = new Date(y, m - 1, d + delta);
    const newDateStr = `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(
      2,
      '0'
    )}-${String(dateObj.getDate()).padStart(2, '0')}`;
    setSelectedDate(newDateStr);
    if (dateObj.getMonth() + 1 !== currentMonth || dateObj.getFullYear() !== currentYear) {
      setCurrentMonth(dateObj.getMonth() + 1);
      setCurrentYear(dateObj.getFullYear());
    }
  };

  // Calendar Grid Computations
  const daysInMonth = new Date(currentYear, currentMonth, 0).getDate();
  const firstDayWeekday = new Date(currentYear, currentMonth - 1, 1).getDay(); // 0 = Sun
  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];
  const currentMonthName = monthNames[currentMonth - 1];

  const weekdayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  // Format selected date nicely (e.g. "Friday, November 13, 2026")
  const selectedDateObj = new Date(`${selectedDate}T00:00:00`);
  const selectedDateFormatted = selectedDateObj.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  const selectedLeave = getLeaveForDate(selectedDate);
  const selectedShift = getShiftForDate(selectedDate);
  const isSelectedToday = selectedDate === todayIso;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING':
      case 'UNDER_REVIEW':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
            <Clock className="w-3 h-3" /> Under Review
          </span>
        );
      case 'APPROVED':
      case 'ROSTER_PENDING':
      case 'IMPLEMENTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
            <CheckCircle2 className="w-3 h-3" /> Accepted
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300">
            <XCircle className="w-3 h-3" /> Rejected
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300">
            {status}
          </span>
        );
    }
  };

  if (loading && !profile) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
          <p className="text-sm text-slate-500">Loading your schedule...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 select-none">
      {/* Header Profile Card */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 p-6 rounded-2xl border border-slate-800 backdrop-blur-xl shadow-lg">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold text-xl shadow-inner">
            <UserIcon className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-white tracking-tight">{profile?.name}</h1>
              <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">
                {profile?.employee_code}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-2 flex-wrap">
              <span>
                Pod: <strong className="text-slate-200">{profile?.pod_name || 'Unassigned'}</strong>
              </span>
              <span>•</span>
              <span>
                Pod Lead: <strong className="text-slate-200">{profile?.pod_lead_name || 'N/A'}</strong>
              </span>
              <span>•</span>
              <span>
                Standard Window:{' '}
                <strong className="text-indigo-300">
                  {profile?.standard_start_time.slice(0, 5)} - {profile?.standard_end_time.slice(0, 5)}
                </strong>{' '}
                ({Math.round((profile?.daily_capacity_minutes || 0) / 60)}h capacity)
              </span>
            </p>
          </div>
        </div>

        <button
          onClick={() => {
            setStartDate(selectedDate);
            setEndDate(selectedDate);
            setShowRequestModal(true);
          }}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium shadow-lg shadow-indigo-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Request Leave / Absence
        </button>
      </div>

      {/* Notifications / Alerts */}
      {error && (
        <div
          className={`p-4 rounded-xl flex items-start justify-between gap-3 text-sm ${
            error.includes('Google Sheets') || error.includes('GOOGLE_SHEETS')
              ? 'bg-amber-500/10 border border-amber-500/30 text-amber-200'
              : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
          }`}
        >
          <div className="flex items-start gap-3 flex-1">
            {error.includes('Google Sheets') || error.includes('GOOGLE_SHEETS') ? (
              <FileSpreadsheet className="w-5 h-5 shrink-0 mt-0.5 text-amber-400" />
            ) : (
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-400" />
            )}
            <div className="space-y-1">
              <p className="font-semibold text-white">{error}</p>
              {(error.includes('Google Sheets') || error.includes('GOOGLE_SHEETS')) && (
                <p className="text-xs text-amber-300/90">
                  Google Sheets export is unavailable because Google OAuth / Service Account is not configured on this server. Direct CSV export is fully operational.
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {(error.includes('Google Sheets') || error.includes('GOOGLE_SHEETS')) && (
              <button
                onClick={() => {
                  setError(null);
                  handleExportMySchedule();
                }}
                className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export CSV Instead</span>
              </button>
            )}
            <button onClick={() => setError(null)} className="text-slate-400 hover:text-white p-1 cursor-pointer">
              <XCircle className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {success && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-3 text-emerald-300">
          <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5 text-emerald-400" />
          <div className="flex-1 text-sm">{success}</div>
          <button onClick={() => setSuccess(null)} className="text-emerald-400 hover:text-emerald-200 cursor-pointer">
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Two Column Summary: Core Assignments & Certified Skills */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Primary Brand / Process Assignments */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <Briefcase className="w-4 h-4 text-indigo-400" /> Primary Dedicated Assignments
          </h2>
          {profile?.primary_assignments.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No dedicated primary assignments recorded.</p>
          ) : (
            <div className="space-y-2">
              {profile?.primary_assignments.map((pa) => (
                <div
                  key={pa.assignment_id}
                  className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs"
                >
                  <div>
                    <p className="font-semibold text-white">{pa.brand_name}</p>
                    <p className="text-[11px] text-slate-400">{pa.process_name}</p>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    Primary Core
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Process Qualifications / Skills */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-purple-400" /> Certified Skills & Backup Qualifications
          </h2>
          {profile?.skills.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No skills registered.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {profile?.skills.map((s) => (
                <div
                  key={s.process_id}
                  className="px-3 py-1.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center gap-2 text-xs"
                >
                  <span className="text-white font-medium">{s.process_name}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    {s.proficiency}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* SECTION 4: MAIN WORKFORCE CALENDAR & DAY-WISE SCHEDULE EXPERIENCE          */}
      {/* ========================================================================= */}
      <div className="space-y-4 pt-2">
        {/* Navigation Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/80 border border-slate-800 p-4 rounded-2xl shadow-sm">
          <div className="flex items-center gap-3">
            {/* View Mode Segmented Switch */}
            <div className="flex items-center rounded-xl bg-slate-950 border border-slate-800 p-1 text-xs">
              <button
                type="button"
                onClick={() => setViewMode('calendar')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all cursor-pointer ${
                  viewMode === 'calendar'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900'
                }`}
              >
                <CalendarDays className="w-3.5 h-3.5" />
                <span>Monthly Calendar</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('day')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all cursor-pointer ${
                  viewMode === 'day'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900'
                }`}
              >
                <Clock className="w-3.5 h-3.5" />
                <span>Day-by-Day View</span>
              </button>
            </div>

            {/* Quick Today Button */}
            <button
              onClick={handleGoToToday}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <Sun className="w-3.5 h-3.5 text-amber-400" />
              <span>Today</span>
            </button>
          </div>

          {/* Month Stepper & Export Controls */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded-xl px-2 py-1">
              <button
                onClick={handlePrevMonth}
                title="Previous month"
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-xs font-bold text-white px-2 tracking-wide font-mono">
                {currentMonthName} {currentYear}
              </span>
              <button
                onClick={handleNextMonth}
                title="Next month"
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {tasks.length > 0 && (
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={handleExportMySchedule}
                  disabled={exporting}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-semibold transition-colors cursor-pointer shadow-2xs"
                  title="Export personal confirmed schedule as CSV"
                >
                  <Download className="w-3.5 h-3.5 text-indigo-400" />
                  <span>{exporting ? 'Exporting...' : 'Export CSV'}</span>
                </button>

                <button
                  type="button"
                  onClick={handleExportGoogleSheets}
                  disabled={exportingGoogle}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-950/80 hover:bg-emerald-900/80 text-emerald-300 border border-emerald-800 text-xs font-semibold transition-colors cursor-pointer shadow-2xs"
                  title="Export schedule to Google Sheets"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                  <span>{exportingGoogle ? 'Exporting...' : 'Google Sheets'}</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* View Mode 1: Monthly Calendar Grid */}
        {viewMode === 'calendar' && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-md space-y-3">
            {/* Legend */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800/80 text-xs text-slate-400">
              <span className="font-semibold text-slate-300">
                {currentMonthName} {currentYear} Schedule ({tasks.length} Assigned Shifts)
              </span>
              <div className="flex items-center gap-4 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                  <span>Today</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
                  <span>Selected</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm bg-indigo-500/30 border border-indigo-500/50" />
                  <span>Confirmed Shift</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm bg-amber-500/30 border border-amber-500/50" />
                  <span>Approved Leave</span>
                </div>
              </div>
            </div>

            {/* Weekday Headers */}
            <div className="grid grid-cols-7 gap-2 text-center text-xs font-bold text-slate-400 py-1">
              {weekdayNames.map((w) => (
                <div key={w} className="uppercase tracking-wider text-[11px]">
                  {w}
                </div>
              ))}
            </div>

            {/* Calendar Days Matrix */}
            <div className="grid grid-cols-7 gap-2">
              {/* Padding empty days for first week */}
              {Array.from({ length: firstDayWeekday }).map((_, idx) => (
                <div
                  key={`empty-${idx}`}
                  className="min-h-[88px] rounded-xl border border-dashed border-slate-800/40 bg-slate-950/20 opacity-40"
                />
              ))}

              {/* Real month days */}
              {Array.from({ length: daysInMonth }).map((_, idx) => {
                const dayNum = idx + 1;
                const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(
                  dayNum
                ).padStart(2, '0')}`;
                const isToday = dateStr === todayIso;
                const isSelected = dateStr === selectedDate;
                const leave = getLeaveForDate(dateStr);
                const shift = getShiftForDate(dateStr);

                return (
                  <button
                    key={dateStr}
                    type="button"
                    onClick={() => setSelectedDate(dateStr)}
                    className={`min-h-[88px] p-2.5 rounded-xl border text-left flex flex-col justify-between transition-all cursor-pointer relative overflow-hidden ${
                      isSelected
                        ? 'bg-indigo-950/70 border-indigo-500 ring-2 ring-indigo-500/60 shadow-md shadow-indigo-950/40'
                        : isToday
                        ? 'bg-slate-900 border-emerald-500/60 ring-1 ring-emerald-500/50'
                        : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/60'
                    }`}
                  >
                    {/* Top Row: Date Number and Status Pills */}
                    <div className="flex items-center justify-between w-full">
                      <span
                        className={`text-xs font-bold ${
                          isSelected
                            ? 'text-white text-sm'
                            : isToday
                            ? 'text-emerald-400 font-black'
                            : 'text-slate-300'
                        }`}
                      >
                        {dayNum}
                      </span>

                      {isToday && (
                        <span className="px-1.5 py-0.2 rounded-full text-[9px] font-extrabold bg-emerald-500 text-slate-950">
                          TODAY
                        </span>
                      )}
                    </div>

                    {/* Middle / Bottom Badges */}
                    <div className="mt-1 w-full space-y-1">
                      {leave.isLeave ? (
                        <div className="px-1.5 py-1 rounded-md bg-amber-500/20 border border-amber-500/40 text-amber-300 text-[10px] font-semibold flex items-center gap-1">
                          <CalendarOff className="w-3 h-3 text-amber-400 shrink-0" />
                          <span className="truncate">{leave.reason || 'Leave'}</span>
                        </div>
                      ) : shift ? (
                        <div className="px-1.5 py-1 rounded-md bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 text-[10px] font-semibold space-y-0.5">
                          <div className="flex items-center gap-1 font-mono text-[9px] text-indigo-200">
                            <Clock className="w-2.5 h-2.5 shrink-0" />
                            <span>
                              {shift.start_time.slice(0, 5)} - {shift.end_time.slice(0, 5)}
                            </span>
                          </div>
                          <p className="truncate text-white font-medium">{shift.brand_name}</p>
                        </div>
                      ) : (
                        <span className="text-[10px] text-slate-600 italic block pl-0.5">Off</span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* View Mode 2: Interactive Day-by-Day View */}
        {viewMode === 'day' && (
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
            {/* Week Ribbon Day Selector */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Weekly Sequence ({getWeekDays(selectedDate)[0]} to {getWeekDays(selectedDate)[6]})
                </span>
                <span className="text-xs text-indigo-400 font-medium">Click any day to jump</span>
              </div>
              <div className="grid grid-cols-7 gap-2">
                {getWeekDays(selectedDate).map((dayStr) => {
                  const dObj = new Date(dayStr + 'T00:00:00');
                  const dayName = dObj.toLocaleDateString(undefined, { weekday: 'short' });
                  const dayNum = dObj.getDate();
                  const isDaySelected = dayStr === selectedDate;
                  const isDayToday = dayStr === todayIso;
                  const dShift = getShiftForDate(dayStr);
                  const dLeave = getLeaveForDate(dayStr);

                  return (
                    <button
                      key={dayStr}
                      type="button"
                      onClick={() => {
                        setSelectedDate(dayStr);
                        setCurrentMonth(dObj.getMonth() + 1);
                        setCurrentYear(dObj.getFullYear());
                      }}
                      className={`p-2.5 rounded-xl border text-center transition-all cursor-pointer flex flex-col items-center justify-center gap-1 ${
                        isDaySelected
                          ? 'bg-indigo-600/30 border-indigo-500 text-white shadow-md ring-1 ring-indigo-500/50'
                          : isDayToday
                          ? 'bg-slate-800/80 border-slate-700 text-white hover:border-slate-600'
                          : 'bg-slate-950/60 border-slate-800/80 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                      }`}
                    >
                      <span className="text-[10px] font-semibold uppercase tracking-wider block">
                        {dayName}
                      </span>
                      <span className={`text-base font-bold ${isDaySelected ? 'text-white' : 'text-slate-200'}`}>
                        {dayNum}
                      </span>
                      {dLeave.isLeave ? (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 whitespace-nowrap">
                          Leave
                        </span>
                      ) : dShift ? (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 whitespace-nowrap">
                          Shift
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-slate-800 text-slate-500 whitespace-nowrap">
                          Off
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Stepper Navigation Controls */}
            <div className="flex items-center justify-between border-t border-slate-800 pt-3">
              <button
                type="button"
                onClick={() => handleStepDay(-1)}
                className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>Previous Day</span>
              </button>

              <div className="text-center">
                <span className="text-xs font-semibold text-slate-300">
                  Step single day forward/backward
                </span>
              </div>

              <button
                type="button"
                onClick={() => handleStepDay(1)}
                className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <span>Next Day</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Selected-Date Detailed Schedule Card */}
        <div className="bg-gradient-to-br from-slate-900 via-indigo-950/20 to-slate-900 border border-slate-800 rounded-2xl p-6 shadow-md space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <CalendarCheck className="w-5 h-5 text-indigo-400" />
                <h3 className="text-lg font-bold text-white">{selectedDateFormatted}</h3>
                {isSelectedToday && (
                  <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-500 text-slate-950 shadow-xs">
                    Today
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Detailed assignment and attendance status for the selected calendar date
              </p>
            </div>

            <div>
              {selectedLeave.isLeave ? (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
                  <CalendarOff className="w-3.5 h-3.5 text-amber-400" />
                  <span>Approved Leave: {selectedLeave.reason}</span>
                </span>
              ) : getShiftsForDate(selectedDate).length > 0 ? (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Confirmed Working Shift ({getShiftsForDate(selectedDate).length} slot{getShiftsForDate(selectedDate).length > 1 ? 's' : ''})</span>
                </span>
              ) : (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1.5">
                  <Sun className="w-3.5 h-3.5 text-slate-400" />
                  <span>Rest Day / Weekly Off</span>
                </span>
              )}
            </div>
          </div>

          {/* Conditional Display Body */}
          {selectedLeave.isLeave ? (
            /* Approved Leave Presentation: Shift area remains blank */
            <div className="p-6 rounded-xl bg-amber-950/20 border border-amber-800/40 space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <CalendarOff className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-amber-200">
                    Approved Absence: {selectedLeave.reason}
                  </h4>
                  <p className="text-xs text-amber-300/80">
                    Status: Approved & Authorized by Operations Manager
                  </p>
                </div>
              </div>

              {selectedLeave.notes && (
                <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-lg border border-amber-900/30">
                  <strong>Notes:</strong> {selectedLeave.notes}
                </p>
              )}

              <p className="text-xs text-slate-400 italic">
                * Active shift allocation is suspended during approved leave. No company shifts are assigned to you on this date.
              </p>
            </div>
          ) : getShiftsForDate(selectedDate).length > 0 ? (
            /* Scheduled Working Shift Presentation: Supports multiple allocations per day */
            <div className="space-y-3">
              {getShiftsForDate(selectedDate).map((shift, idx) => (
                <div key={shift.id || idx} className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 rounded-xl bg-slate-950/80 border border-slate-800">
                  <div className="space-y-1">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Briefcase className="w-3.5 h-3.5 text-indigo-400" /> Company & Brand
                    </span>
                    <p className="text-base font-bold text-white pt-1">{shift.brand_name}</p>
                    <p className="text-xs text-indigo-300 font-medium">{shift.process_name}</p>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-indigo-400" /> Shift Hours
                    </span>
                    <p className="text-base font-bold text-white font-mono pt-1">
                      {shift.start_time.slice(0, 5)} - {shift.end_time.slice(0, 5)}
                    </p>
                    <p className="text-xs text-slate-400">
                      Standard working allocation
                    </p>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-indigo-400" /> Assignment Role
                    </span>
                    <p className="text-base font-bold text-white pt-1 capitalize">
                      {shift.allocation_type.replace(/_/g, ' ')}
                    </p>
                    <span className="text-xs text-emerald-400 font-medium">
                      {shift.roster_name || 'Production Roster'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* Rest Day / Weekly Off Presentation */
            <div className="p-8 rounded-xl bg-slate-950/40 border border-slate-800 text-center space-y-2">
              <Sun className="w-8 h-8 text-amber-400/60 mx-auto" />
              <h4 className="text-sm font-bold text-slate-300">Rest Day / Weekly Off</h4>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                You have no scheduled shifts or leave booked for {selectedDateFormatted}. Enjoy your rest day!
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Requests History */}
      <div className="space-y-4 pt-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <FileText className="w-5 h-5 text-indigo-400" /> Leave & Absence Request History
        </h2>

        {requests.length === 0 ? (
          <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-400 space-y-2">
            <FileText className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-sm font-medium">No leave requests submitted yet.</p>
            <p className="text-xs text-slate-500">
              Submit an absence request whenever you need time off, sick leave, or weekly off rescheduling.
            </p>
          </div>
        ) : (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/60 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Submitted</th>
                    <th className="px-4 py-3">Dates</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Reason / Notes</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Manager Feedback</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {requests.map((req) => (
                    <tr key={req.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-400">
                        {new Date(req.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 font-medium text-white text-xs whitespace-nowrap">
                        {req.start_date} {req.start_date !== req.end_date ? `to ${req.end_date}` : ''}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        <span className="font-mono text-indigo-300">{req.reason_type}</span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-300 max-w-xs truncate">
                        {req.notes || <span className="text-slate-600 italic">None</span>}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">{getStatusBadge(req.status)}</td>
                      <td className="px-4 py-3 text-xs text-slate-400 max-w-xs truncate">
                        {req.review_notes || (
                          <span className="text-slate-600 italic">Pending manager review</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Leave Request Modal */}
      {showRequestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Send className="w-5 h-5 text-indigo-400" /> Request Leave or Absence
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Send absence request to Operations Manager for review and conflict resolution
                </p>
              </div>
              <button
                onClick={() => setShowRequestModal(false)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmitRequest} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Absence Category</label>
                <select
                  value={reasonType}
                  onChange={(e) => setReasonType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="PLANNED_LEAVE">PLANNED_LEAVE (Annual / Personal Time Off)</option>
                  <option value="SICK_LEAVE">SICK_LEAVE (Medical / Unplanned Leave)</option>
                  <option value="APPROVED_OFF">APPROVED_OFF (Weekly Off Swap / Adjustment)</option>
                  <option value="COMP_OFF">COMP_OFF (Compensatory Off)</option>
                  <option value="TRAINING">TRAINING (Professional Development)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Reason / Notes (Required)</label>
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  required
                  placeholder="e.g., Annual family event / doctor appointment"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500 placeholder-slate-600"
                />
              </div>

              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 flex items-start gap-2">
                <HelpCircle className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                <span>
                  Submitting this request will not alter your schedule immediately. The Operations Manager will review the request, reassign any conflicting shifts to eligible qualified backups, and notify you upon resolution.
                </span>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRequestModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || notes.length < 3}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium flex items-center gap-2 shadow-lg shadow-indigo-600/30 cursor-pointer"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" /> Submitting...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" /> Send Request
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmployeePortalScreen;
