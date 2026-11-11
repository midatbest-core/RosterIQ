import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { api } from '../../services/api';
import { BackupCandidate } from '../../services/types';
import { StatusBadge } from '../common/StatusBadge';
import {
  Users,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Clock,
  ArrowRightLeft,
  Calendar,
  Briefcase,
  Layers,
  AlertTriangle,
} from 'lucide-react';

interface ReassignSlot {
  date: string;
  brand_process_id: string;
  brand_name: string;
  process_name: string;
  start_time: string;
  end_time: string;
  source_employee_id?: string;
  source_employee_name?: string;
}

interface ReassignmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  rosterId: string;
  slot: ReassignSlot | null;
  onReassigned: () => void;
}

export const ReassignmentModal: React.FC<ReassignmentModalProps> = ({
  isOpen,
  onClose,
  rosterId,
  slot,
  onReassigned,
}) => {
  const [candidates, setCandidates] = useState<BackupCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>('');
  const [confirmCrossPod, setConfirmCrossPod] = useState(false);
  const [reason, setReason] = useState('Medical absence coverage');
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<{
    is_eligible: boolean;
    rejection_reason?: string | null;
    allocation_type: string;
    requires_ops_manager_approval: boolean;
    affected_conflicts_count: number;
  } | null>(null);
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    if (isOpen && slot && rosterId) {
      loadCandidates();
    } else {
      setCandidates([]);
      setSelectedCandidateId('');
      setConfirmCrossPod(false);
      setPreview(null);
      setError(null);
    }
  }, [isOpen, slot, rosterId]);

  const loadCandidates = async () => {
    if (!slot) return;
    try {
      setLoading(true);
      setError(null);
      const list = await api.getBackupCandidates(
        rosterId,
        slot.brand_process_id,
        slot.date,
        slot.start_time,
        slot.end_time
      );
      setCandidates(list);
      if (list.length > 0) {
        setSelectedCandidateId(list[0].employee_id);
        runPreview(list[0].employee_id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load backup candidates');
    } finally {
      setLoading(false);
    }
  };

  const runPreview = async (candidateId: string) => {
    if (!slot) return;
    try {
      const res = await api.previewReassignment({
        roster_id: rosterId,
        date: slot.date,
        brand_process_id: slot.brand_process_id,
        start_time: slot.start_time,
        end_time: slot.end_time,
        target_employee_id: candidateId,
        source_employee_id: slot.source_employee_id,
      });
      setPreview(res);
      setConfirmCrossPod(false);
    } catch (err: any) {
      setError(err.message || 'Failed to preview reassignment');
    }
  };

  const handleSelectCandidate = (candidateId: string) => {
    setSelectedCandidateId(candidateId);
    runPreview(candidateId);
  };

  const handleApply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!slot || !selectedCandidateId) return;

    if (preview?.requires_ops_manager_approval && !confirmCrossPod) {
      setError('Explicit Operations Manager authorization is required for cross-pod assignment.');
      return;
    }

    try {
      setApplying(true);
      setError(null);
      await api.applyReassignment({
        roster_id: rosterId,
        date: slot.date,
        brand_process_id: slot.brand_process_id,
        start_time: slot.start_time,
        end_time: slot.end_time,
        target_employee_id: selectedCandidateId,
        source_employee_id: slot.source_employee_id,
        reason,
        confirm_cross_pod_approval: confirmCrossPod,
      });
      onReassigned();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to apply reassignment');
    } finally {
      setApplying(false);
    }
  };

  if (!slot) return null;

  const selectedCandidate = candidates.find((c) => c.employee_id === selectedCandidateId);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Backup Candidate Discovery & Reassignment"
      subtitle="Resolve uncovered slot or employee absence"
      maxWidth="xl"
    >
      <form onSubmit={handleApply} className="space-y-5">
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Slot Context Card */}
        <div className="p-4 bg-slate-50 border border-slate-200/80 rounded-xl space-y-2 text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200/60">
            <span className="font-bold text-slate-800 text-sm flex items-center gap-1.5">
              <Briefcase className="w-4 h-4 text-indigo-600" />
              {slot.brand_name} · {slot.process_name}
            </span>
            <span className="font-mono font-semibold text-slate-600 bg-white px-2.5 py-0.5 rounded-md border border-slate-200">
              {slot.date}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-slate-600 pt-1">
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>
                Required Interval: <strong>{slot.start_time} - {slot.end_time}</strong>
              </span>
            </div>
            {slot.source_employee_name && (
              <div className="flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-slate-400" />
                <span>
                  Primary Absentee: <strong>{slot.source_employee_name}</strong>
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Candidates Section */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-indigo-600" />
              Ranked Eligible Backup Candidates ({candidates.length})
            </h4>
            <span className="text-[11px] text-slate-500">Filtered by active skill & zero shift overlap</span>
          </div>

          {loading ? (
            <div className="py-8 text-center text-xs text-slate-500">
              Evaluating candidate pool across all pods...
            </div>
          ) : candidates.length === 0 ? (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
              No eligible backup candidates found with active skills and free capacity for this slot.
            </div>
          ) : (
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {candidates.map((c) => {
                const isSelected = selectedCandidateId === c.employee_id;
                return (
                  <div
                    key={c.employee_id}
                    onClick={() => handleSelectCandidate(c.employee_id)}
                    className={`p-3 rounded-xl border text-xs transition-all cursor-pointer flex items-center justify-between ${
                      isSelected
                        ? 'border-indigo-600 bg-indigo-50/40 ring-1 ring-indigo-500/20'
                        : 'border-slate-200 hover:border-slate-300 bg-white'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                          isSelected ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-slate-300'
                        }`}
                      >
                        {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                      </div>
                      <div>
                        <span className="font-bold text-slate-900">{c.name}</span>
                        <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-500">
                          <span>Pod: {c.pod_name || 'Unassigned'}</span>
                          {c.prefers_off_on_day && (
                            <span className="text-amber-700 font-medium">(Soft Day-Off Preference)</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {c.is_same_pod ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Same-Pod
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                          Cross-Pod (Approval Required)
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Cross-Pod Governance Authorization Card */}
        {preview?.requires_ops_manager_approval && (
          <div className="p-4 bg-purple-50/70 border border-purple-200 rounded-xl space-y-3">
            <div className="flex items-start gap-2.5">
              <ShieldAlert className="w-5 h-5 text-purple-700 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h5 className="text-xs font-bold text-purple-950">
                  Operations Manager Cross-Pod Authorization Required
                </h5>
                <p className="text-[11px] text-purple-900/80 leading-relaxed">
                  Candidate <strong>{selectedCandidate?.name}</strong> belongs to an external pod. In accordance with organizational governance, cross-pod allocations require explicit managerial sign-off and will be recorded in the audit log.
                </p>
              </div>
            </div>

            <label className="flex items-center gap-2.5 pt-2 border-t border-purple-200/70 cursor-pointer">
              <input
                type="checkbox"
                checked={confirmCrossPod}
                onChange={(e) => setConfirmCrossPod(e.target.checked)}
                className="w-4 h-4 rounded-xs border-purple-300 text-purple-600 focus:ring-purple-500"
              />
              <span className="text-xs font-semibold text-purple-900 select-none">
                I hereby authorize this cross-pod workforce allocation
              </span>
            </label>
          </div>
        )}

        {/* Reason Input */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Reassignment Reason / Audit Justification
          </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
            placeholder="e.g. Approved medical leave coverage"
            className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        {/* Actions */}
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
            disabled={
              applying ||
              !selectedCandidateId ||
              (preview?.requires_ops_manager_approval && !confirmCrossPod)
            }
            className="flex items-center gap-2 px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-xs shadow-indigo-600/30 cursor-pointer disabled:opacity-50"
          >
            <ArrowRightLeft className="w-3.5 h-3.5" />
            <span>{applying ? 'Applying Reassignment...' : 'Confirm & Apply Reassignment'}</span>
          </button>
        </div>
      </form>
    </Modal>
  );
};

