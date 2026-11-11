import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Employee, Pod, EmployeeUnavailability } from '../services/types';
import { Users, Plus, CalendarOff, Settings2, Trash2 } from 'lucide-react';

export const EmployeesScreen: React.FC = () => {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [pods, setPods] = useState<Pod[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Add Employee Form State
  const [showAddEmp, setShowAddEmp] = useState(false);
  const [empCode, setEmpCode] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [podId, setPodId] = useState('');
  const [start, setStart] = useState('09:00:00');
  const [end, setEnd] = useState('18:00:00');

  // Add Pod Form State
  const [showAddPod, setShowAddPod] = useState(false);
  const [newPodName, setNewPodName] = useState('');

  // Availability & Leave Modal State
  const [selectedEmp, setSelectedEmp] = useState<Employee | null>(null);
  const [unavailabilities, setUnavailabilities] = useState<EmployeeUnavailability[]>([]);
  const [prefDays, setPrefDays] = useState<string>('5,6');
  const [leaveDate, setLeaveDate] = useState('2026-11-10');
  const [leaveReason, setLeaveReason] = useState<'PLANNED_LEAVE' | 'SICK_LEAVE' | 'COMP_OFF'>('PLANNED_LEAVE');
  const [leaveNotes, setLeaveNotes] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [eList, pList] = await Promise.all([api.getEmployees(), api.getPods()]);
      setEmployees(eList);
      setPods(pList);
      if (pList.length > 0 && !podId) {
        setPodId(pList[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load employees');
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
        name,
        email,
        pod_id: podId || null,
        standard_start_time: start,
        standard_end_time: end,
        daily_capacity_minutes: 540,
      });
      setShowAddEmp(false);
      setEmpCode('');
      setName('');
      setEmail('');
      await loadData();
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
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to create pod');
    } finally {
      setLoading(false);
    }
  };

  const openAvailabilityModal = async (emp: Employee) => {
    setSelectedEmp(emp);
    try {
      const [uList, prefs] = await Promise.all([
        api.getEmployeeUnavailability(emp.id),
        api.getEmployeePreferences(emp.id),
      ]);
      setUnavailabilities(uList);
      if (prefs) setPrefDays(prefs.preferred_weekly_off_days);
    } catch (err: any) {
      setError(err.message || 'Failed to load availability');
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
      const uList = await api.getEmployeeUnavailability(selectedEmp.id);
      setUnavailabilities(uList);
      setLeaveNotes('');
    } catch (err: any) {
      setError(err.message || 'Failed to add leave');
    }
  };

  const handleDeleteLeave = async (uId: string) => {
    if (!selectedEmp) return;
    try {
      await api.deleteEmployeeUnavailability(selectedEmp.id, uId);
      const uList = await api.getEmployeeUnavailability(selectedEmp.id);
      setUnavailabilities(uList);
    } catch (err: any) {
      setError(err.message || 'Failed to delete leave');
    }
  };

  const handleSavePreferences = async () => {
    if (!selectedEmp) return;
    try {
      await api.setEmployeePreferences(selectedEmp.id, prefDays);
      alert('Weekly-off preferences saved successfully!');
    } catch (err: any) {
      setError(err.message || 'Failed to update preferences');
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="w-6 h-6 text-indigo-600" />
          <div>
            <h1 className="text-xl font-bold text-slate-900">Workforce & Pod Management</h1>
            <p className="text-xs text-slate-500">
              Manage employees, pods, weekly off preferences, and approved leaves
            </p>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => setShowAddPod(true)}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white font-medium text-sm rounded-lg flex items-center gap-2 shadow-sm transition"
          >
            <Plus className="w-4 h-4" /> Add Pod
          </button>
          <button
            onClick={() => setShowAddEmp(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded-lg flex items-center gap-2 shadow-sm transition"
          >
            <Plus className="w-4 h-4" /> Add Employee
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 text-sm rounded-xl flex justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-bold">✕</button>
        </div>
      )}

      {/* Employees Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-100 text-slate-700 font-semibold uppercase tracking-wider border-b border-slate-200">
              <th className="p-3">Code</th>
              <th className="p-3">Name</th>
              <th className="p-3">Email</th>
              <th className="p-3">Pod</th>
              <th className="p-3">Shift Hours</th>
              <th className="p-3">Status</th>
              <th className="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {employees.map((emp) => {
              const pod = pods.find((p) => p.id === emp.pod_id);
              return (
                <tr key={emp.id} className="hover:bg-slate-50 transition">
                  <td className="p-3 font-semibold text-slate-900">{emp.employee_code}</td>
                  <td className="p-3 font-medium text-slate-900">{emp.name}</td>
                  <td className="p-3 text-slate-600">{emp.email}</td>
                  <td className="p-3">
                    <span className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded-md font-medium">
                      {pod ? pod.name : 'Unassigned'}
                    </span>
                  </td>
                  <td className="p-3 text-slate-700 font-medium">
                    {emp.standard_start_time} - {emp.standard_end_time}
                  </td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded-full font-bold text-[10px] bg-emerald-100 text-emerald-800">
                      {emp.status}
                    </span>
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => openAvailabilityModal(emp)}
                      className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded flex items-center gap-1.5 ml-auto transition"
                    >
                      <CalendarOff className="w-3.5 h-3.5 text-indigo-600" />
                      Availability & Leave
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Add Pod Modal */}
      {showAddPod && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-sm p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900">Create Operational Pod</h2>
            <form onSubmit={handleCreatePod} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Pod Name</label>
                <input
                  type="text"
                  placeholder="Pod Epsilon - Fintech"
                  value={newPodName}
                  onChange={(e) => setNewPodName(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  required
                />
              </div>
              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddPod(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 text-sm font-medium rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg"
                >
                  Create Pod
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Employee Modal */}
      {showAddEmp && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900">Add New Employee</h2>
            <form onSubmit={handleCreateEmp} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Employee Code</label>
                <input
                  type="text"
                  placeholder="EMP-033"
                  value={empCode}
                  onChange={(e) => setEmpCode(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
                <input
                  type="text"
                  placeholder="Ravi Shastri"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Email</label>
                <input
                  type="email"
                  placeholder="ravi@datastraw.io"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Assigned Pod</label>
                <select
                  value={podId}
                  onChange={(e) => setPodId(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  {pods.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddEmp(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 text-sm font-medium rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg"
                >
                  Save Employee
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Availability & Leave Management Modal */}
      {selectedEmp && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg p-6 space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">
                  Availability & Leave: {selectedEmp.name}
                </h2>
                <p className="text-xs text-slate-500">{selectedEmp.employee_code} | {selectedEmp.email}</p>
              </div>
              <button onClick={() => setSelectedEmp(null)} className="font-bold text-slate-400 hover:text-slate-600">
                ✕
              </button>
            </div>

            {/* Weekly-off Preferences (Soft Constraint) */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
              <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                <Settings2 className="w-4 h-4 text-indigo-600" /> Preferred Weekly-Off Days (Soft Preference)
              </span>
              <p className="text-[11px] text-slate-500">
                Comma-separated weekday numbers (0=Mon, 1=Tue, ..., 5=Sat, 6=Sun). E.g., "5,6" for weekends.
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={prefDays}
                  onChange={(e) => setPrefDays(e.target.value)}
                  className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs w-32 bg-white"
                />
                <button
                  type="button"
                  onClick={handleSavePreferences}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold"
                >
                  Save Preferences
                </button>
              </div>
            </div>

            {/* Approved Leave List (Hard Constraint) */}
            <div className="space-y-3">
              <span className="text-xs font-bold text-slate-800 block">
                Approved Absences & Planned Leaves ({unavailabilities.length})
              </span>
              {unavailabilities.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No approved absences on record.</p>
              ) : (
                <div className="space-y-1.5">
                  {unavailabilities.map((u) => (
                    <div
                      key={u.id}
                      className="p-2.5 bg-rose-50/60 border border-rose-200 rounded-lg text-xs flex items-center justify-between"
                    >
                      <div>
                        <span className="font-bold text-rose-900 mr-2">{u.date}</span>
                        <span className="px-1.5 py-0.5 bg-rose-200 text-rose-800 rounded font-semibold text-[10px]">
                          {u.reason_type}
                        </span>
                        {u.notes && <span className="text-slate-600 ml-2">({u.notes})</span>}
                      </div>
                      <button
                        onClick={() => handleDeleteLeave(u.id)}
                        className="text-rose-600 hover:text-rose-800 p-1"
                        title="Delete absence"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Record New Absence */}
            <form onSubmit={handleAddLeave} className="p-4 border border-slate-200 rounded-xl space-y-3 bg-white">
              <span className="text-xs font-bold text-slate-800 block">Record Approved Absence</span>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">Date</label>
                  <input
                    type="date"
                    value={leaveDate}
                    onChange={(e) => setLeaveDate(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">Absence Type</label>
                  <select
                    value={leaveReason}
                    onChange={(e: any) => setLeaveReason(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs bg-white"
                  >
                    <option value="PLANNED_LEAVE">PLANNED_LEAVE</option>
                    <option value="SICK_LEAVE">SICK_LEAVE</option>
                    <option value="COMP_OFF">COMP_OFF</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">Notes / Reason</label>
                <input
                  type="text"
                  placeholder="Doctor appointment, personal leave, etc."
                  value={leaveNotes}
                  onChange={(e) => setLeaveNotes(e.target.value)}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                />
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-sm"
                >
                  Record Absence
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
