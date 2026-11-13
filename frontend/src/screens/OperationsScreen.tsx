import React, { useState, useEffect } from 'react';
import { api, ApiError } from '../services/api';
import {
  Brand,
  ProcessItem,
  BrandProcess,
  PrimaryAssignment,
  Employee,
  BrandOperatingSchedule,
  ValidationErrorDetail,
  CreatedCredentials,
} from '../services/types';
import { Modal } from '../components/common/Modal';
import { ValidationErrorPopupModal } from '../components/common/ValidationErrorPopupModal';
import { DistributeCredentialsModal } from '../components/common/DistributeCredentialsModal';
import {
  Briefcase,
  Layers,
  GitFork,
  Plus,
  CheckCircle2,
  Calendar,
  Clock,
  Sparkles,
  CalendarOff,
  Users,
  CalendarCheck,
  ArrowRight,
  ExternalLink,
  Sun,
  AlertTriangle,
  ShieldAlert,
} from 'lucide-react';

interface OperationsScreenProps {
  initialSubTab?: 'brands' | 'assignments';
  onNavigateToConflicts?: () => void;
}

export const OperationsScreen: React.FC<OperationsScreenProps> = ({
  initialSubTab = 'brands',
  onNavigateToConflicts,
}) => {
  const [subTab, setSubTab] = useState<'brands' | 'assignments'>(initialSubTab);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [processes, setProcesses] = useState<ProcessItem[]>([]);
  const [brandProcesses, setBrandProcesses] = useState<BrandProcess[]>([]);
  const [assignments, setAssignments] = useState<PrimaryAssignment[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Add Brand Form
  const [showAddBrand, setShowAddBrand] = useState(false);
  const [brandCode, setBrandCode] = useState('');
  const [brandName, setBrandName] = useState('');

  // Add Process Form
  const [showAddProcess, setShowAddProcess] = useState(false);
  const [processCode, setProcessCode] = useState('');
  const [processName, setProcessName] = useState('');
  const [processDesc, setProcessDesc] = useState('');

  // Add BrandProcess Form
  const [showAddBp, setShowAddBp] = useState(false);
  const [selectedBrandId, setSelectedBrandId] = useState('');
  const [selectedProcessId, setSelectedProcessId] = useState('');

  // Add Assignment Form
  const [showAddAssignment, setShowAddAssignment] = useState(false);
  const [assignEmpId, setAssignEmpId] = useState('');
  const [assignBpId, setAssignBpId] = useState('');
  const [effectiveFrom, setEffectiveFrom] = useState('2026-11-01');

  // Brand Schedule Inspection Modal
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [selectedBrandForModal, setSelectedBrandForModal] = useState<Brand | null>(null);
  const [brandSchedule, setBrandSchedule] = useState<BrandOperatingSchedule | null>(null);
  const [loadingSchedule, setLoadingSchedule] = useState(false);

  // Validation Error Popup State
  const [validationErrors, setValidationErrors] = useState<ValidationErrorDetail[]>([]);
  const [showValidationPopup, setShowValidationPopup] = useState(false);
  const [validationFallbackMsg, setValidationFallbackMsg] = useState('');

  // Credentials Distribution State
  const [createdCreds, setCreatedCreds] = useState<CreatedCredentials | null>(null);
  const [showCredsModal, setShowCredsModal] = useState(false);

  // Conflict Check Notification State
  const [conflictNotification, setConflictNotification] = useState<{
    title: string;
    message: string;
    total_conflicts: number;
    hard_conflicts: number;
  } | null>(null);

  const handleOpenBrandSchedule = async (brand: Brand) => {
    setSelectedBrandForModal(brand);
    setScheduleModalOpen(true);
    setLoadingSchedule(true);
    try {
      const data = await api.getBrandOperatingSchedule(brand.id);
      setBrandSchedule(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingSchedule(false);
    }
  };

  useEffect(() => {
    loadOperationsData();
  }, []);

  const loadOperationsData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [bList, prList, bpList, aList, eList] = await Promise.all([
        api.getBrands(),
        api.getProcesses(),
        api.getBrandProcesses(),
        api.getAssignments(),
        api.getEmployees(),
      ]);
      setBrands(bList);
      setProcesses(prList);
      setBrandProcesses(bpList);
      setAssignments(aList);
      setEmployees(eList);
      if (bList.length > 0 && !selectedBrandId) setSelectedBrandId(bList[0].id);
      if (prList.length > 0 && !selectedProcessId) setSelectedProcessId(prList[0].id);
      if (eList.length > 0 && !assignEmpId) setAssignEmpId(eList[0].id);
      if (bpList.length > 0 && !assignBpId) setAssignBpId(bpList[0].id);
    } catch (err: any) {
      setError(err.message || 'Failed to load operations data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBrand = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      const created = await api.createBrand(brandCode.trim(), brandName.trim());
      setShowAddBrand(false);
      setBrandCode('');
      setBrandName('');
      await loadOperationsData();

      // Show login credentials distribution popup
      const cleanCode = (created.code || brandCode).toLowerCase().replace(/_/g, '').replace(/-/g, '');
      setCreatedCreds({
        name: created.name || brandName,
        email: created.login_email || `brand.${cleanCode}@example.com`,
        role: 'Brand User',
        temporaryPassword: created.temporary_password || 'BrandPass123!',
        code: created.code || brandCode,
      });
      setShowCredsModal(true);
    } catch (err: any) {
      if (err instanceof ApiError && err.validationErrors && err.validationErrors.length > 0) {
        setValidationErrors(err.validationErrors);
        setValidationFallbackMsg(err.message);
        setShowValidationPopup(true);
      } else if (err.validationErrors && err.validationErrors.length > 0) {
        setValidationErrors(err.validationErrors);
        setValidationFallbackMsg(err.message);
        setShowValidationPopup(true);
      } else {
        const msg = err.message || 'Failed to create brand';
        setError(msg);
        setValidationErrors([{ field: 'code', fieldLabel: 'Brand Code / Name', reason: msg }]);
        setValidationFallbackMsg(msg);
        setShowValidationPopup(true);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProcess = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      await api.createProcess(processCode.trim(), processName.trim(), processDesc.trim());
      setShowAddProcess(false);
      setProcessCode('');
      setProcessName('');
      setProcessDesc('');
      await loadOperationsData();
    } catch (err: any) {
      if (err.validationErrors && err.validationErrors.length > 0) {
        setValidationErrors(err.validationErrors);
        setValidationFallbackMsg(err.message);
        setShowValidationPopup(true);
      } else {
        const msg = err.message || 'Failed to create process';
        setError(msg);
        setValidationErrors([{ field: 'code', fieldLabel: 'Process Code / Name', reason: msg }]);
        setValidationFallbackMsg(msg);
        setShowValidationPopup(true);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBrandProcess = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const res = await api.createBrandProcess(selectedBrandId, selectedProcessId);
      setShowAddBp(false);
      await loadOperationsData();
      if (res.conflict_check) {
        const b = brands.find((brand) => brand.id === selectedBrandId);
        const p = processes.find((proc) => proc.id === selectedProcessId);
        setConflictNotification({
          title: `Linked ${b?.name || 'Brand'} with ${p?.name || 'Process'}`,
          message: res.conflict_check.message,
          total_conflicts: res.conflict_check.total_conflicts,
          hard_conflicts: res.conflict_check.hard_conflicts,
        });
      }
    } catch (err: any) {
      setError(err.message || 'Failed to link brand with process');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const res = await api.createAssignment({
        employee_id: assignEmpId,
        brand_process_id: assignBpId,
        effective_from: effectiveFrom,
        priority: 1,
      });
      setShowAddAssignment(false);
      await loadOperationsData();
      if (res.conflict_check) {
        const emp = employees.find((e) => e.id === assignEmpId);
        setConflictNotification({
          title: `Primary Assignment Created for ${emp?.name || 'Employee'}`,
          message: res.conflict_check.message,
          total_conflicts: res.conflict_check.total_conflicts,
          hard_conflicts: res.conflict_check.hard_conflicts,
        });
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create assignment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Sub-Tabs Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200/60">
          <button
            onClick={() => setSubTab('brands')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
              subTab === 'brands'
                ? 'bg-white text-indigo-700 shadow-2xs border border-slate-200/50'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Briefcase className="w-3.5 h-3.5" />
            <span>Brands & Processes ({brands.length} Brands)</span>
          </button>
          <button
            onClick={() => setSubTab('assignments')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
              subTab === 'assignments'
                ? 'bg-white text-indigo-700 shadow-2xs border border-slate-200/50'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <GitFork className="w-3.5 h-3.5" />
            <span>Primary Assignments ({assignments.length})</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          {subTab === 'brands' && (
            <div className="flex gap-2">
              <button
                onClick={() => setShowAddBrand(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Brand</span>
              </button>
              <button
                onClick={() => setShowAddProcess(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Process</span>
              </button>
              <button
                onClick={() => setShowAddBp(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Link Brand & Process</span>
              </button>
            </div>
          )}
          {subTab === 'assignments' && (
            <button
              onClick={() => setShowAddAssignment(true)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Assignment</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl">
          {error}
        </div>
      )}

      {/* Tab 1: Brands & Processes */}
      {subTab === 'brands' && (
        <div className="space-y-6">
          {/* Active Brand Catalog */}
          <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Brand Directory</h3>
                <p className="text-xs text-slate-500">
                  15 operational brands (~80% single-resource, 20% multi-resource)
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-5">
              {brands.map((b) => {
                const attachedBps = brandProcesses.filter((bp) => bp.brand_id === b.id);
                return (
                  <div
                    key={b.id}
                    onClick={() => handleOpenBrandSchedule(b)}
                    className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50 space-y-2.5 text-xs cursor-pointer hover:border-indigo-400 hover:shadow-md hover:bg-white transition-all group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                        {b.name}
                      </span>
                      <span className="font-mono text-[10px] bg-white px-2 py-0.5 rounded border text-slate-600">
                        {b.code}
                      </span>
                    </div>
                    <div className="space-y-1.5 pt-1 border-t border-slate-200/60">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-semibold text-slate-400 uppercase">
                          Active Processes ({attachedBps.length})
                        </span>
                        <span className="text-[10px] font-bold text-indigo-600 flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform">
                          <span>View Schedule</span>
                          <ArrowRight className="w-3 h-3" />
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {attachedBps.map((bp) => {
                          const proc = processes.find((p) => p.id === bp.process_id);
                          return (
                            <span
                              key={bp.id}
                              className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-[10px] font-semibold text-indigo-700"
                            >
                              {proc?.name || 'Process'}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Primary Assignments */}
      {subTab === 'assignments' && (
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-4 py-3">Employee</th>
                  <th className="px-4 py-3">Brand & Process</th>
                  <th className="px-4 py-3">Effective From</th>
                  <th className="px-4 py-3">Priority</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {assignments.map((a) => {
                  const emp = employees.find((e) => e.id === a.employee_id);
                  const bp = brandProcesses.find((p) => p.id === a.brand_process_id);
                  const brand = brands.find((b) => b.id === bp?.brand_id);
                  const proc = processes.find((pr) => pr.id === bp?.process_id);
                  return (
                    <tr key={a.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-4 py-3 font-semibold text-slate-900">{emp?.name || 'Unknown'}</td>
                      <td className="px-4 py-3 text-slate-700">
                        {brand?.name} · <span className="text-indigo-600 font-semibold">{proc?.name}</span>
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-600">{a.effective_from}</td>
                      <td className="px-4 py-3 font-mono font-medium">#{a.priority} (Primary)</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Active
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add Brand Modal */}
      <Modal
        isOpen={showAddBrand}
        onClose={() => setShowAddBrand(false)}
        title="Register Operational Brand"
        subtitle="Onboard a new brand to receive scheduled workforce allocations"
        maxWidth="md"
      >
        <form onSubmit={handleCreateBrand} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Brand Code</label>
            <input
              type="text"
              value={brandCode}
              onChange={(e) => setBrandCode(e.target.value)}
              required
              placeholder="e.g. AURORA"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono uppercase"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Brand Name</label>
            <input
              type="text"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              required
              placeholder="e.g. Aurora Wellness"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            />
          </div>
          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setShowAddBrand(false)}
              className="px-4 py-2 border rounded-lg text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold cursor-pointer"
            >
              Save Brand
            </button>
          </div>
        </form>
      </Modal>

      {/* Add Process Modal */}
      <Modal
        isOpen={showAddProcess}
        onClose={() => setShowAddProcess(false)}
        title="Add Operational Process"
        subtitle="Create a new standardized operational capability"
        maxWidth="md"
      >
        <form onSubmit={handleCreateProcess} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Process Code</label>
            <input
              type="text"
              value={processCode}
              onChange={(e) => setProcessCode(e.target.value)}
              required
              placeholder="e.g. RET"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono uppercase"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Process Name</label>
            <input
              type="text"
              value={processName}
              onChange={(e) => setProcessName(e.target.value)}
              required
              placeholder="e.g. Customer Retention"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Description</label>
            <input
              type="text"
              value={processDesc}
              onChange={(e) => setProcessDesc(e.target.value)}
              placeholder="e.g. Retention and escalation desk"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            />
          </div>
          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setShowAddProcess(false)}
              className="px-4 py-2 border rounded-lg text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold cursor-pointer"
            >
              Save Process
            </button>
          </div>
        </form>
      </Modal>

      {/* Link Brand & Process Modal */}
      <Modal
        isOpen={showAddBp}
        onClose={() => setShowAddBp(false)}
        title="Link Brand with Process"
        subtitle="Configure an active operational process under a brand"
        maxWidth="md"
      >
        <form onSubmit={handleCreateBrandProcess} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Brand</label>
            <select
              value={selectedBrandId}
              onChange={(e) => setSelectedBrandId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            >
              {brands.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({b.code})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Process</label>
            <select
              value={selectedProcessId}
              onChange={(e) => setSelectedProcessId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            >
              {processes.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.code})
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setShowAddBp(false)}
              className="px-4 py-2 border rounded-lg text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold cursor-pointer"
            >
              Link Process
            </button>
          </div>
        </form>
      </Modal>

      {/* Add Assignment Modal */}
      <Modal
        isOpen={showAddAssignment}
        onClose={() => setShowAddAssignment(false)}
        title="Create Primary Assignment"
        subtitle="Assign an employee as primary resource for a brand-process"
        maxWidth="md"
      >
        <form onSubmit={handleCreateAssignment} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Employee</label>
            <select
              value={assignEmpId}
              onChange={(e) => setAssignEmpId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            >
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name} ({e.employee_code})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Brand Process</label>
            <select
              value={assignBpId}
              onChange={(e) => setAssignBpId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            >
              {brandProcesses.map((bp) => {
                const b = brands.find((item) => item.id === bp.brand_id);
                const p = processes.find((item) => item.id === bp.process_id);
                return (
                  <option key={bp.id} value={bp.id}>
                    {b?.name} — {p?.name}
                  </option>
                );
              })}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Effective From</label>
            <input
              type="date"
              value={effectiveFrom}
              onChange={(e) => setEffectiveFrom(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            />
          </div>
          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setShowAddAssignment(false)}
              className="px-4 py-2 border rounded-lg text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold cursor-pointer"
            >
              Create Assignment
            </button>
          </div>
        </form>
      </Modal>

      {/* Brand Operating Schedule Modal */}
      <Modal
        isOpen={scheduleModalOpen}
        onClose={() => setScheduleModalOpen(false)}
        title={`${selectedBrandForModal?.name || 'Brand'} — Operating Schedule & Pattern`}
        subtitle={`Brand Code: ${selectedBrandForModal?.code} · Status: ${selectedBrandForModal?.status || 'ACTIVE'}`}
        maxWidth="4xl"
      >
        {loadingSchedule ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs font-semibold text-slate-700">Loading operational schedule and patterns...</p>
          </div>
        ) : brandSchedule ? (
          <div className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
            <div className="p-3 bg-indigo-50/70 border border-indigo-100 rounded-xl text-xs text-indigo-900 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sun className="w-4 h-4 text-indigo-600 shrink-0" />
                <span>
                  Showing operational calendars for <strong>{brandSchedule.processes.length}</strong> process(es) associated with {brandSchedule.brand_name}.
                </span>
              </div>
            </div>

            {brandSchedule.processes.length === 0 ? (
              <div className="py-10 text-center text-xs text-slate-500">
                No active processes configured for this brand.
              </div>
            ) : (
              <div className="space-y-4">
                {brandSchedule.processes.map((proc) => {
                  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
                  const is365 = proc.pattern_label.includes('365');
                  const isMonSat = proc.pattern_label.includes('Saturday');
                  const isMonFri = proc.pattern_label.includes('Friday');

                  return (
                    <div
                      key={proc.brand_process_id}
                      className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-3.5"
                    >
                      {/* Process Header & Operating Pattern Badge */}
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-100">
                        <div className="flex items-center gap-2">
                          <span className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-xs">
                            {proc.process_code}
                          </span>
                          <div>
                            <h4 className="text-sm font-bold text-slate-900">{proc.process_name}</h4>
                            <span className="text-[10px] text-slate-400 font-mono">
                              ID: {proc.brand_process_id.slice(0, 8)}...
                            </span>
                          </div>
                        </div>

                        {/* Operating Pattern Pill */}
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1.5 shadow-2xs ${
                              is365
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : isMonSat
                                ? 'bg-amber-50 text-amber-700 border-amber-200'
                                : isMonFri
                                ? 'bg-blue-50 text-blue-700 border-blue-200'
                                : 'bg-purple-50 text-purple-700 border-purple-200'
                            }`}
                          >
                            <CalendarCheck className="w-3.5 h-3.5" />
                            {proc.pattern_label}
                          </span>
                        </div>
                      </div>

                      {/* 7-Day Weekly Grid */}
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                          Weekly Operating Days
                        </span>
                        <div className="grid grid-cols-7 gap-1.5">
                          {dayNames.map((name, idx) => {
                            const isOperating = proc.operating_days.includes(idx);
                            return (
                              <div
                                key={name}
                                className={`py-1.5 px-2 rounded-lg text-center text-xs font-bold transition-all border ${
                                  isOperating
                                    ? 'bg-indigo-600 text-white border-indigo-700 shadow-2xs'
                                    : 'bg-slate-50 text-slate-400 border-slate-200/80 line-through'
                                }`}
                              >
                                <span className="block text-[10px] uppercase font-semibold opacity-80">
                                  {name}
                                </span>
                                <span className="text-[11px] font-extrabold">
                                  {isOperating ? 'OPEN' : 'OFF'}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Operating Details Grid */}
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50/70 p-3 rounded-xl border border-slate-200/60 text-xs">
                        <div>
                          <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                            Operating Hours
                          </span>
                          <span className="font-bold text-slate-800 flex items-center gap-1 mt-0.5">
                            <Clock className="w-3.5 h-3.5 text-indigo-600" />
                            {proc.start_time.slice(0, 5)} – {proc.end_time.slice(0, 5)}
                          </span>
                        </div>

                        <div>
                          <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                            Min Staffing
                          </span>
                          <span className="font-semibold text-slate-800 mt-0.5 block">
                            Weekday: <strong>{proc.min_staffing_weekday}</strong> | Weekend:{' '}
                            <strong>{proc.min_staffing_weekend}</strong>
                          </span>
                        </div>

                        <div>
                          <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                            Holiday Policy
                          </span>
                          <span
                            className={`inline-block mt-0.5 text-[11px] font-bold px-2 py-0.5 rounded border ${
                              proc.holiday_behavior === 'CLOSED'
                                ? 'bg-rose-50 text-rose-700 border-rose-200'
                                : proc.holiday_behavior === 'REDUCED'
                                ? 'bg-amber-50 text-amber-700 border-amber-200'
                                : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            }`}
                          >
                            {proc.holiday_behavior} (Min: {proc.min_staffing_holiday})
                          </span>
                        </div>
                      </div>

                      {/* Date Overrides */}
                      {proc.overrides.length > 0 && (
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                            Date-Specific Overrides ({proc.overrides.length})
                          </span>
                          <div className="space-y-1">
                            {proc.overrides.map((ov, oi) => (
                              <div
                                key={oi}
                                className="flex items-center justify-between text-xs p-2 bg-amber-50/50 rounded-lg border border-amber-200/70 text-amber-900"
                              >
                                <div className="flex items-center gap-2">
                                  <CalendarOff className="w-3.5 h-3.5 text-amber-600" />
                                  <span className="font-mono font-bold">{ov.date}</span>
                                  <span className="text-slate-600">— {ov.reason || 'Operational adjustment'}</span>
                                </div>
                                <span className="font-bold text-[11px]">
                                  {ov.is_closed ? 'CLOSED' : `Min Staffing: ${ov.override_min_staffing}`}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Assigned Primary Staff */}
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                          Primary Assigned Agents ({proc.assigned_employees.length})
                        </span>
                        {proc.assigned_employees.length === 0 ? (
                          <span className="text-xs text-slate-400 italic">No primary agents assigned yet.</span>
                        ) : (
                          <div className="flex flex-wrap gap-1.5">
                            {proc.assigned_employees.map((emp) => (
                              <div
                                key={emp.id}
                                className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-xs flex items-center gap-1.5 shadow-2xs"
                              >
                                <span className="font-bold text-slate-900">{emp.name}</span>
                                <span className="text-[10px] font-mono text-slate-400">({emp.code})</span>
                                <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-50 text-indigo-700 font-semibold border border-indigo-100">
                                  {emp.pod_name}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : null}
      </Modal>

      {/* Validation Error Popup Modal */}
      <ValidationErrorPopupModal
        isOpen={showValidationPopup}
        onClose={() => setShowValidationPopup(false)}
        title="Invalid Brand Input Data"
        subtitle="The server rejected the brand creation request because one or more fields contain invalid data."
        entityName="Brand"
        errors={validationErrors}
        fallbackMessage={validationFallbackMsg}
      />

      {/* Login Credentials Distribution Modal */}
      <DistributeCredentialsModal
        isOpen={showCredsModal}
        onClose={() => setShowCredsModal(false)}
        credentials={createdCreds}
        onOpenConflicts={onNavigateToConflicts}
      />

      {/* Conflict Check Feedback Modal */}
      {conflictNotification && (
        <Modal
          isOpen={!!conflictNotification}
          onClose={() => setConflictNotification(null)}
          title="Automatic Conflict Check Complete"
          subtitle={conflictNotification.title}
          maxWidth="md"
        >
          <div className="space-y-4 p-1">
            <div className={`p-4 rounded-xl border flex items-start gap-3 ${
              conflictNotification.total_conflicts > 0
                ? 'bg-amber-50 border-amber-200 text-amber-950'
                : 'bg-emerald-50 border-emerald-200 text-emerald-950'
            }`}>
              <div className={`p-2 rounded-lg shrink-0 ${
                conflictNotification.total_conflicts > 0
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-emerald-100 text-emerald-700'
              }`}>
                {conflictNotification.total_conflicts > 0 ? (
                  <AlertTriangle className="w-5 h-5" />
                ) : (
                  <CheckCircle2 className="w-5 h-5" />
                )}
              </div>
              <div className="space-y-1">
                <h4 className="text-sm font-bold">
                  {conflictNotification.total_conflicts === 0
                    ? '✓ No Conflicts Detected'
                    : `⚠️ ${conflictNotification.total_conflicts} Conflict(s) Detected (${conflictNotification.hard_conflicts} Hard Violations)`}
                </h4>
                <p className="text-xs leading-relaxed opacity-90">
                  {conflictNotification.message}
                </p>
                {conflictNotification.total_conflicts > 0 && (
                  <p className="text-[11px] text-amber-800 font-medium pt-1">
                    Newly linked operational processes introduce minimum staffing demands and shift coverage requirements into active rosters.
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setConflictNotification(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
              >
                Dismiss
              </button>
              {conflictNotification.total_conflicts > 0 && onNavigateToConflicts && (
                <button
                  type="button"
                  onClick={() => {
                    setConflictNotification(null);
                    onNavigateToConflicts();
                  }}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <ShieldAlert className="w-4 h-4" />
                  <span>Open Conflict Resolver</span>
                </button>
              )}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

