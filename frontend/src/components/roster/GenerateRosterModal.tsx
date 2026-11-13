import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { api } from '../../services/api';
import { RosterSummary } from '../../services/types';
import {
  Sparkles,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  Clock,
  Layers,
  Users,
} from 'lucide-react';

interface GenerateRosterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerated: (newRoster: RosterSummary) => void;
}

export const GenerateRosterModal: React.FC<GenerateRosterModalProps> = ({
  isOpen,
  onClose,
  onGenerated,
}) => {
  const [month, setMonth] = useState(11);
  const [year, setYear] = useState(2026);
  const [name, setName] = useState('November 2026 Production Roster');
  const [userEditedName, setUserEditedName] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RosterSummary | null>(null);

  const months = [
    { value: 1, label: 'January' },
    { value: 2, label: 'February' },
    { value: 3, label: 'March' },
    { value: 4, label: 'April' },
    { value: 5, label: 'May' },
    { value: 6, label: 'June' },
    { value: 7, label: 'July' },
    { value: 8, label: 'August' },
    { value: 9, label: 'September' },
    { value: 10, label: 'October' },
    { value: 11, label: 'November' },
    { value: 12, label: 'December' },
  ];

  const handleMonthChange = (newMonth: number) => {
    setMonth(newMonth);
    const mLabel = months.find((m) => m.value === newMonth)?.label || 'Monthly';
    if (!userEditedName) {
      setName(`${mLabel} ${year} Production Roster`);
    } else {
      // If the user's name has any other month name in it, replace it
      for (const m of months) {
        if (name.includes(m.label)) {
          setName(name.replace(m.label, mLabel));
          break;
        }
      }
    }
  };

  const handleYearChange = (newYear: number) => {
    setYear(newYear);
    const mLabel = months.find((m) => m.value === month)?.label || 'Monthly';
    if (!userEditedName) {
      setName(`${mLabel} ${newYear} Production Roster`);
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      const generated = await api.generateRoster(name, month, year);
      setResult(generated);
      onGenerated(generated);
    } catch (err: any) {
      setError(err.message || 'Roster generation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDone = () => {
    setResult(null);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Deterministic Roster Generation"
      subtitle="Generate compliant, zero-jitter monthly employee schedules"
      maxWidth="lg"
    >
      {!result ? (
        <form onSubmit={handleGenerate} className="space-y-5">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Form Fields */}
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Roster Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setUserEditedName(true);
                }}
                required
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:outline-hidden focus:border-indigo-500 focus:bg-white transition-all"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Target Month
                </label>
                <select
                  value={month}
                  onChange={(e) => handleMonthChange(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-800 focus:outline-hidden focus:border-indigo-500"
                >
                  {months.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Calendar Year
                </label>
                <input
                  type="number"
                  value={year}
                  onChange={(e) => handleYearChange(Number(e.target.value))}
                  min={2024}
                  max={2030}
                  required
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-800 focus:outline-hidden focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Engine Guarantees Notice */}
          <div className="p-3.5 bg-indigo-50/60 border border-indigo-100 rounded-xl space-y-2 text-xs text-indigo-950">
            <span className="font-bold flex items-center gap-1.5 text-indigo-900">
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              Scheduling Engine Rules
            </span>
            <ul className="list-disc pl-4 space-y-1 text-indigo-900/80 text-[11px]">
              <li>
                <strong>Precedence:</strong> Date Override &rarr; Recurring Weekday &rarr; Holiday Behaviour.
              </li>
              <li>
                <strong>Constraints:</strong> At most 1 continuous same-day shift per employee. No split shifts.
              </li>
              <li>
                <strong>Governance:</strong> Primary allocations prioritized. Cross-pod backups surfaced for approval.
              </li>
            </ul>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg text-xs font-medium cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-xs shadow-indigo-600/30 cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{loading ? 'Executing Scheduling Engine...' : 'Generate Roster'}</span>
            </button>
          </div>
        </form>
      ) : (
        /* Result Summary Screen */
        <div className="space-y-5">
          <div className="text-center space-y-2 py-2">
            <div className="w-12 h-12 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h4 className="text-base font-bold text-slate-900">Roster Generated Successfully</h4>
            <p className="text-xs text-slate-500">
              {result.name} (v{result.version}) has been created in DRAFT status.
            </p>
          </div>

          {/* KPI Matrix */}
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/80">
              <span className="text-[10px] text-slate-500 font-semibold uppercase">Total Shifts</span>
              <p className="text-lg font-bold text-slate-900 mt-0.5">{result.total_shifts}</p>
            </div>
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/80">
              <span className="text-[10px] text-slate-500 font-semibold uppercase">Allocations</span>
              <p className="text-lg font-bold text-indigo-600 mt-0.5">{result.total_allocations}</p>
            </div>
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/80">
              <span className="text-[10px] text-slate-500 font-semibold uppercase">Hard Violations</span>
              <p className="text-lg font-bold text-rose-600 mt-0.5">{result.hard_violations_count}</p>
            </div>
          </div>

          {result.hard_violations_count > 0 ? (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 space-y-1">
              <span className="font-bold flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                Action Required Before Publishing
              </span>
              <p className="text-[11px] leading-relaxed">
                {result.hard_violations_count} uncovered demand slots or absence conflicts require backup reassignment in the Conflicts Workspace.
              </p>
            </div>
          ) : (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Zero hard conflicts! This roster is eligible for publishing.</span>
            </div>
          )}

          <div className="flex justify-end pt-3 border-t border-slate-100">
            <button
              onClick={handleDone}
              className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
            >
              Open in Calendar
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
};

