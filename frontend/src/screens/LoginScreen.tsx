import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { User } from '../services/types';
import {
  Calendar,
  Lock,
  Mail,
  ArrowRight,
  ShieldAlert,
  Building2,
  Users,
  Shield,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface LoginScreenProps {
  onLoginSuccess: (user: User) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState(import.meta.env.DEV ? 'admin@example.com' : '');
  const [password, setPassword] = useState(import.meta.env.DEV ? 'AdminPass123!' : '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pod-Wise Quick Login Directory
  const [demoAccounts, setDemoAccounts] = useState<any | null>(null);
  const [showDirectory, setShowDirectory] = useState(false);
  const [selectedPodTab, setSelectedPodTab] = useState<string>('');

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    fetch('/api/v1/auth/demo-accounts')
      .then((r) => r.json())
      .then((data) => {
        setDemoAccounts(data);
        const podKeys = Object.keys(data.employees_by_pod || {});
        if (podKeys.length > 0) {
          setSelectedPodTab(podKeys[0]);
        }
      })
      .catch((err) => console.log('Demo directory unavailable:', err));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      const user = await api.login(email, password);
      onLoginSuccess(user);
    } catch (err: any) {
      setError(err.message || 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  const selectQuickLogin = (uEmail: string, roleHint: string) => {
    setEmail(uEmail);
    // In dev demo seeds, standard role passwords apply:
    if (roleHint === 'ADMIN') setPassword('AdminPass123!');
    else if (roleHint === 'OPERATIONS_MANAGER') setPassword('OpsManager123!');
    else if (roleHint === 'POD_LEAD') setPassword('PodLeadPass123!');
    else if (roleHint === 'BRAND_USER') setPassword('BrandPass123!');
    else if (roleHint === 'EMPLOYEE') setPassword('EmployeePass123!');
    else setPassword('SecretPass123!');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200/80 dark:border-slate-800 overflow-hidden my-6">
        {/* Header Branding */}
        <div className="p-8 pb-6 text-center space-y-3 bg-gradient-to-b from-indigo-50/50 to-white dark:from-slate-800/40 dark:to-slate-900">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/30">
            <Calendar className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">RosterIQ</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Workforce Operations & Deterministic Scheduling Suite
            </p>
          </div>
        </div>

        {/* Form Body */}
        <div className="p-8 pt-2 space-y-5">
          {error && (
            <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs rounded-xl flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="name@example.com"
                  className="w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-900 dark:text-white focus:outline-hidden focus:border-indigo-500 transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••••••"
                  className="w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-900 dark:text-white focus:outline-hidden focus:border-indigo-500 transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-xs shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
            >
              <span>{loading ? 'Authenticating...' : 'Sign In to Workspace'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </form>

          {/* Quick-Fill Fast Demo Credentials & Directory (DEV-only) */}
          {import.meta.env.DEV && (
            <>
              <div className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Quick Role Credentials
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowDirectory(!showDirectory)}
                    className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    <span>{showDirectory ? 'Hide Full Pod Directory' : 'Explore All 58 Demo Accounts'}</span>
                    {showDirectory ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <button
                    type="button"
                    onClick={() => selectQuickLogin('admin@example.com', 'ADMIN')}
                    className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-500 text-left transition-colors cursor-pointer bg-slate-50/50 dark:bg-slate-950/40"
                  >
                    <span className="font-semibold text-slate-900 dark:text-white block text-[11px] flex items-center gap-1">
                      <Shield className="w-3 h-3 text-indigo-500" /> Admin
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono truncate block">admin@example.com</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => selectQuickLogin('ops@example.com', 'OPERATIONS_MANAGER')}
                    className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-purple-300 dark:hover:border-purple-500 text-left transition-colors cursor-pointer bg-slate-50/50 dark:bg-slate-950/40"
                  >
                    <span className="font-semibold text-slate-900 dark:text-white block text-[11px] flex items-center gap-1">
                      <Users className="w-3 h-3 text-purple-500" /> Ops Mgr
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono truncate block">ops@example.com</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => selectQuickLogin('podalpha.lead@example.com', 'POD_LEAD')}
                    className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-emerald-300 dark:hover:border-emerald-500 text-left transition-colors cursor-pointer bg-slate-50/50 dark:bg-slate-950/40"
                  >
                    <span className="font-semibold text-slate-900 dark:text-white block text-[11px] flex items-center gap-1">
                      <Layers className="w-3 h-3 text-emerald-500" /> Pod Alpha
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono truncate block">podalpha.lead@...</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => selectQuickLogin('brand.stellar@example.com', 'BRAND_USER')}
                    className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-amber-300 dark:hover:border-amber-500 text-left transition-colors cursor-pointer bg-slate-50/50 dark:bg-slate-950/40"
                  >
                    <span className="font-semibold text-slate-900 dark:text-white block text-[11px] flex items-center gap-1">
                      <Building2 className="w-3 h-3 text-amber-500" /> Brand User
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono truncate block">brand.stellar@...</span>
                  </button>
                </div>
              </div>

              {/* Pod-Wise Interactive Directory Drawer */}
              {showDirectory && demoAccounts && (
                <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3 animate-in fade-in">
                  <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 block">
                    Pod-Wise Workforce & Brand User Accounts
                  </span>

                  {/* Pod Tabs */}
                  <div className="flex flex-wrap gap-1.5 border-b border-slate-200 dark:border-slate-800 pb-2">
                    {Object.keys(demoAccounts.employees_by_pod || {}).map((podName) => (
                      <button
                        key={podName}
                        type="button"
                        onClick={() => setSelectedPodTab(podName)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                          selectedPodTab === podName
                            ? 'bg-indigo-600 text-white shadow-sm'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900'
                        }`}
                      >
                        {podName}
                      </button>
                    ))}
                  </div>

                  {/* Employees in selected Pod */}
                  {selectedPodTab && demoAccounts.employees_by_pod[selectedPodTab] && (
                    <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                      {demoAccounts.employees_by_pod[selectedPodTab].map((emp: any) => (
                        <div
                          key={emp.id}
                          onClick={() => selectQuickLogin(emp.email, 'EMPLOYEE')}
                          className="p-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 hover:border-indigo-400 dark:hover:border-indigo-500 flex items-center justify-between cursor-pointer text-xs"
                        >
                          <div>
                            <span className="font-semibold text-slate-900 dark:text-white block">{emp.name}</span>
                            <span className="text-[10px] text-slate-500 font-mono">{emp.email}</span>
                          </div>
                          <span className="px-2 py-0.5 rounded text-[10px] bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
                            Select Employee
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
export default LoginScreen;
