import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Employee, Pod, EmployeeUnavailability, User } from '../services/types';
import { Modal } from '../components/common/Modal';
import { DetailDrawer } from '../components/layout/DetailDrawer';
import { StatusBadge } from '../components/common/StatusBadge';
import {
  Users,
  Network,
  CalendarOff,
  Plus,
  Search,
  Filter,
  Clock,
  Mail,
  ShieldCheck,
  CheckCircle2,
  Trash2,
  Briefcase,
  Sliders,
} from 'lucide-react';

interface WorkforceScreenProps {
  initialSubTab?: 'employees' | 'pods' | 'leaves';
  searchQuery?: string;
  currentUser?: User | null;
}

export const WorkforceScreen: React.FC<WorkforceScreenProps> = ({
  initialSubTab = 'employees',
  searchQuery = '',
  currentUser,
}) => {
  const isPodLead = currentUser?.role === 'POD_LEAD';
  const [subTab, setSubTab] = useState<'employees' | 'pods' | 'leaves'>(initialSubTab);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [pods, setPods] = useState<Pod[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Add Employee Modal
  const [showAddEmp, setShowAddEmp] = useState(false);
  const [empCode, setEmpCode] = useState('');
  const [empName, setEmpName] = useState('');
  const [empEmail, setEmpEmail] = useState('');
  const [empPodId, setEmpPodId] = useState('');
  const [start, setStart] = useState('09:00:00');
  const [end, setEnd] = useState('18:00:00');

  // Add Pod Modal
  const [showAddPod, setShowAddPod] = useState(false);
  const [newPodName, setNewPodName] = useState('');

  // Selected Employee Profile Drawer
  const [selectedEmp, setSelectedEmp] = useState<Employee | null>(null);
  const [isEmpDrawerOpen, setIsEmpDrawerOpen] = useState(false);
  const [empUnavailabilities, setEmpUnavailabilities] = useState<EmployeeUnavailability[]>([]);
  const [prefDays, setPrefDays] = useState('5,6');

  // Add Leave Form State
  const [leaveDate, setLeaveDate] = useState('2026-11-15');
  const [leaveReason, setLeaveReason] = useState<
    'PLANNED_LEAVE' | 'SICK_LEAVE' | 'APPROVED_OFF' | 'COMP_OFF' | 'TRAINING'
  >('PLANNED_LEAVE');
  const [leaveNotes, setLeaveNotes] = useState('');

  useEffect(() => {
    loadWorkforceData();
  }, []);

  const loadWorkforceData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [eList, pList] = await Promise.all([api.getEmployees(), api.getPods()]);
      setEmployees(eList);
      setPods(pList);
      if (pList.length > 0 && !empPodId) setEmpPodId(pList[0].id);
    } catch (err: any) {
      setError(err.message || 'Failed to load workforce data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEmp = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await api.createEmployee({
        employee_code: empCode,
        name: empName,
        email: empEmail,
        pod_id: empPodId || null,
        standard_start_time: start,
        standard_end_time: end,
        daily_capacity_minutes: 540,
      });
      setShowAddEmp(false);
      setEmpCode('');
      setEmpName('');
      setEmpEmail('');
      await loadWorkforceData();
    } catch (err: any) {
      setError(err.message || 'Failed to create employee');
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePod = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await api.createPod(newPodName);
      setShowAddPod(false);
      setNewPodName('');
      await loadWorkforceData();
    } catch (err: any) {
      setError(err.message || 'Failed to create pod');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenEmpDrawer = async (emp: Employee) => {
    setSelectedEmp(emp);
    setIsEmpDrawerOpen(true);
    try {
      const [uList, prefs] = await Promise.all([
        api.getEmployeeUnavailability(emp.id),
        api.getEmployeePreferences(emp.id),
      ]);
      setEmpUnavailabilities(uList);
      if (prefs) setPrefDays(prefs.preferred_weekly_off_days);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddLeave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEmp) return;
    try {
      await api.addEmployeeUnavailability(selectedEmp.id, {
        date: leaveDate,
        reason_type: leaveReason,
        is_approved: true,
        notes: leaveNotes,
      });
      const updated = await api.getEmployeeUnavailability(selectedEmp.id);
      setEmpUnavailabilities(updated);
      setLeaveNotes('');
    } catch (err: any) {
      alert(err.message || 'Failed to record absence');
    }
  };

  const handleDeleteLeave = async (unavailabilityId: string) => {
    if (!selectedEmp) return;
    try {
      await api.deleteEmployeeUnavailability(selectedEmp.id, unavailabilityId);
      const updated = await api.getEmployeeUnavailability(selectedEmp.id);
      setEmpUnavailabilities(updated);
    } catch (err: any) {
      alert(err.message || 'Failed to delete leave');
    }
  };

  const handleSavePreferences = async () => {
    if (!selectedEmp) return;
    try {
      await api.setEmployeePreferences(selectedEmp.id, prefDays, 'Standard weekly off preference');
      alert('Preferences saved successfully!');
    } catch (err: any) {
      alert(err.message || 'Failed to save preferences');
    }
  };

  const targetEmployees = isPodLead && currentUser?.pod_id
    ? employees.filter((emp) => emp.pod_id === currentUser.pod_id)
    : employees;

  const filteredEmployees = targetEmployees.filter((emp) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      emp.name.toLowerCase().includes(q) ||
      emp.employee_code.toLowerCase().includes(q) ||
      emp.email.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Sub-Tabs Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200/60">
          {isPodLead ? (
            <button
              onClick={() => setSubTab('employees')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-white text-indigo-700 shadow-2xs border border-slate-200/50"
            >
              <Users className="w-3.5 h-3.5" />
              <span>Pod Members ({filteredEmployees.length})</span>
            </button>
          ) : (
            <>
              <button
                onClick={() => setSubTab('employees')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                  subTab === 'employees'
                    ? 'bg-white text-indigo-700 shadow-2xs border border-slate-200/50'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>Employees Directory ({employees.length})</span>
              </button>
              <button
                onClick={() => setSubTab('pods')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                  subTab === 'pods'
                    ? 'bg-white text-indigo-700 shadow-2xs border border-slate-200/50'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Network className="w-3.5 h-3.5" />
                <span>Pods & Leads ({pods.length})</span>
              </button>
              <button
                onClick={() => setSubTab('leaves')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                  subTab === 'leaves'
                    ? 'bg-white text-indigo-700 shadow-2xs border border-slate-200/50'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <CalendarOff className="w-3.5 h-3.5" />
                <span>Availability & Leave</span>
              </button>
            </>
          )}
        </div>

        {!isPodLead && (
          <div className="flex items-center gap-2">
            {subTab === 'employees' && (
              <button
                onClick={() => setShowAddEmp(true)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Employee</span>
              </button>
            )}
            {subTab === 'pods' && (
              <button
                onClick={() => setShowAddPod(true)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Create Pod</span>
              </button>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl">
          {error}
        </div>
      )}

      {/* Tab 1: Employees Directory */}
      {subTab === 'employees' && (
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-4 py-3">Employee Name</th>
                  <th className="px-4 py-3">Code</th>
                  <th className="px-4 py-3">Home Pod</th>
                  <th className="px-4 py-3">Standard Shift</th>
                  <th className="px-4 py-3">Capacity</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredEmployees.map((emp) => {
                  const pod = pods.find((p) => p.id === emp.pod_id);
                  return (
                    <tr
                      key={emp.id}
                      onClick={() => handleOpenEmpDrawer(emp)}
                      className="hover:bg-slate-50/60 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900">{emp.name}</div>
                        <div className="text-[11px] text-slate-500 font-mono">{emp.email}</div>
                      </td>
                      <td className="px-4 py-3 font-mono font-medium text-slate-700">
                        {emp.employee_code}
                      </td>
                      <td className="px-4 py-3">
                        {pod ? (
                          <span className="inline-flex items-center gap-1 font-medium px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200 text-[11px]">
                            <Network className="w-3 h-3 text-indigo-500" />
                            {pod.name}
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">Unassigned</span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-600">
                        {emp.standard_start_time} - {emp.standard_end_time}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {Math.round(emp.daily_capacity_minutes / 60)} hrs / day
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {emp.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold">
                          Profile &rarr;
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Pods Directory */}
      {subTab === 'pods' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {pods.map((pod) => {
            const members = employees.filter((e) => e.pod_id === pod.id);
            return (
              <div
                key={pod.id}
                className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-2xs space-y-3"
              >
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
                      <Network className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-900 text-sm">{pod.name}</h4>
                      <span className="text-[11px] text-slate-500 font-medium">
                        {members.length} Members
                      </span>
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Pod Members
                  </span>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {members.map((m) => (
                      <div
                        key={m.id}
                        className="p-1.5 rounded-md bg-slate-50 text-slate-700 text-xs flex items-center justify-between"
                      >
                        <span className="font-medium truncate">{m.name}</span>
                        <span className="font-mono text-[10px] text-slate-400">{m.employee_code}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Tab 3: Availability & Leave Overview */}
      {subTab === 'leaves' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-2xs space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Workforce Availability & Absences</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Select an employee from the directory to review their approved leaves, medical off-days, and weekly-off preferences.
            </p>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/60 text-xs text-slate-700 space-y-2">
            <span className="font-bold text-slate-900 block">Assessment Scenario 4.F Context:</span>
            <p className="leading-relaxed">
              Diya Patel is the sole Customer Support primary employee on <strong>Kavya Organics</strong>. When an approved medical leave is recorded for Nov 02–06, the scheduling engine flags an <code>UNCOVERED_SLOT</code> conflict. The Operations Manager can then discover ranked backup candidates and authorize cross-pod coverage with full audit tracking.
            </p>
          </div>
        </div>
      )}

      {/* Add Employee Modal */}
      <Modal
        isOpen={showAddEmp}
        onClose={() => setShowAddEmp(false)}
        title="Add Employee to Workforce"
        subtitle="Onboard a new operations resource with standard shift capacity"
      >
        <form onSubmit={handleCreateEmp} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Employee Code</label>
              <input
                type="text"
                value={empCode}
                onChange={(e) => setEmpCode(e.target.value)}
                required
                placeholder="e.g. EMP040"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
              <input
                type="text"
                value={empName}
                onChange={(e) => setEmpName(e.target.value)}
                required
                placeholder="e.g. Rohan Verma"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
            <input
              type="email"
              value={empEmail}
              onChange={(e) => setEmpEmail(e.target.value)}
              required
              placeholder="rohan@example.com"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Home Pod</label>
            <select
              value={empPodId}
              onChange={(e) => setEmpPodId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            >
              {pods.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Standard Start</label>
              <input
                type="text"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Standard End</label>
              <input
                type="text"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setShowAddEmp(false)}
              className="px-4 py-2 border rounded-lg text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold cursor-pointer"
            >
              Save Employee
            </button>
          </div>
        </form>
      </Modal>

      {/* Add Pod Modal */}
      <Modal
        isOpen={showAddPod}
        onClose={() => setShowAddPod(false)}
        title="Create Operational Pod"
        subtitle="Group employees under organizational pods"
        maxWidth="md"
      >
        <form onSubmit={handleCreatePod} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Pod Name</label>
            <input
              type="text"
              value={newPodName}
              onChange={(e) => setNewPodName(e.target.value)}
              required
              placeholder="e.g. Epsilon Pod"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            />
          </div>
          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setShowAddPod(false)}
              className="px-4 py-2 border rounded-lg text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold cursor-pointer"
            >
              Create Pod
            </button>
          </div>
        </form>
      </Modal>

      {/* Employee Profile & Leave Drawer */}
      <DetailDrawer
        isOpen={isEmpDrawerOpen}
        onClose={() => setIsEmpDrawerOpen(false)}
        title={selectedEmp?.name || 'Employee Profile'}
        subtitle={`Code: ${selectedEmp?.employee_code || ''} · ${selectedEmp?.email || ''}`}
        width="lg"
      >
        <div className="space-y-6">
          {/* Shift & Capacity Details */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-2 text-xs">
            <span className="font-bold text-slate-900 uppercase tracking-wider text-[10px]">
              Shift & Working Hours
            </span>
            <div className="grid grid-cols-2 gap-2 text-slate-700 pt-1">
              <div>
                <span className="text-slate-500">Working Window:</span>
                <p className="font-mono font-bold mt-0.5">
                  {selectedEmp?.standard_start_time} - {selectedEmp?.standard_end_time}
                </p>
              </div>
              <div>
                <span className="text-slate-500">Daily Capacity:</span>
                <p className="font-bold mt-0.5">
                  {Math.round((selectedEmp?.daily_capacity_minutes || 0) / 60)} hours / day
                </p>
              </div>
            </div>
          </div>

          {/* Weekly Off Preference */}
          <div className="space-y-3 bg-white p-4 rounded-xl border border-slate-200/80 text-xs">
            <span className="font-bold text-slate-900 uppercase tracking-wider text-[10px] flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-indigo-600" />
              Soft Weekly-Off Preference
            </span>
            <div className="space-y-2">
              <label className="block text-slate-600">Preferred Off Days (0=Mon, 6=Sun):</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={prefDays}
                  onChange={(e) => setPrefDays(e.target.value)}
                  placeholder="e.g. 5,6 for Sat/Sun"
                  className="flex-1 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono"
                />
                <button
                  type="button"
                  onClick={handleSavePreferences}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold cursor-pointer"
                >
                  Save
                </button>
              </div>
            </div>
          </div>

          {/* Record Approved Leave / Absence Form */}
          <div className="space-y-3 bg-white p-4 rounded-xl border border-slate-200/80 text-xs">
            <span className="font-bold text-slate-900 uppercase tracking-wider text-[10px] flex items-center gap-1.5">
              <CalendarOff className="w-3.5 h-3.5 text-amber-600" />
              Record Approved Absence / Leave
            </span>

            <form onSubmit={handleAddLeave} className="space-y-3 pt-1">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-600 mb-1">Absence Date</label>
                  <input
                    type="date"
                    value={leaveDate}
                    onChange={(e) => setLeaveDate(e.target.value)}
                    required
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-slate-600 mb-1">Reason Type</label>
                  <select
                    value={leaveReason}
                    onChange={(e: any) => setLeaveReason(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  >
                    <option value="PLANNED_LEAVE">Planned Leave</option>
                    <option value="SICK_LEAVE">Sick Leave (Medical)</option>
                    <option value="COMP_OFF">Compensatory Off</option>
                    <option value="TRAINING">Training / Offsite</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-600 mb-1">Notes</label>
                <input
                  type="text"
                  value={leaveNotes}
                  onChange={(e) => setLeaveNotes(e.target.value)}
                  placeholder="e.g. Hospitalization, doctor appointment"
                  className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold cursor-pointer shadow-xs"
              >
                Record Approved Absence
              </button>
            </form>
          </div>

          {/* Existing Unavailabilities List */}
          <div className="space-y-2">
            <span className="font-bold text-slate-900 uppercase tracking-wider text-[10px] block">
              Logged Absences ({empUnavailabilities.length})
            </span>
            {empUnavailabilities.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No approved absences on record.</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {empUnavailabilities.map((u) => (
                  <div
                    key={u.id}
                    className="p-2.5 rounded-lg border border-slate-200 bg-slate-50 flex items-center justify-between text-xs"
                  >
                    <div>
                      <span className="font-bold text-slate-900 font-mono">{u.date}</span>
                      <span className="ml-2 text-slate-600">{u.reason_type.replace('_', ' ')}</span>
                      {u.notes && <p className="text-[11px] text-slate-500">{u.notes}</p>}
                    </div>
                    <button
                      onClick={() => handleDeleteLeave(u.id)}
                      className="text-rose-600 hover:text-rose-800 p-1"
                      title="Remove absence"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </DetailDrawer>
    </div>
  );
};

