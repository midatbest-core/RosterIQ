import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { User, DemoRole, QuickLoginAccount } from '../services/types';
import { RosterIQLogo } from '../components/brand/RosterIQLogo';
import {
  Lock,
  Mail,
  ArrowRight,
  ShieldAlert,
  Building2,
  Users,
  Shield,
  Layers,
  UserCheck,
  Sparkles,
  Loader2,
  KeyRound,
  Check,
  Copy,
  Zap,
} from 'lucide-react';

interface LoginScreenProps {
  onLoginSuccess: (user: User) => void;
}

const DEFAULT_DEMO_ROLES: DemoRole[] = [
  {
    role: 'ADMIN',
    name: 'System Admin',
    description: 'Full company-wide visibility, system configuration & audits',
    email: 'admin.staging@rosteriq.io',
  },
  {
    role: 'OPERATIONS_MANAGER',
    name: 'Operations Manager',
    description: 'Roster generation, constraint rules & requests review center',
    email: 'ops.staging@rosteriq.io',
  },
  {
    role: 'POD_LEAD',
    name: 'Pod Lead',
    description: 'Pod Alpha team scheduling, workforce allocation & leave submissions',
    email: 'lead.staging@rosteriq.io',
  },
  {
    role: 'BRAND_USER',
    name: 'Brand User',
    description: 'Kavya Organic Skincare portal, operating calendar & change requests',
    email: 'brand.staging@rosteriq.io',
  },
  {
    role: 'EMPLOYEE',
    name: 'Employee',
    description: 'Aarav Sharma (EMP-001) personal schedule, shifts & leave requests',
    email: 'employee.staging@rosteriq.io',
  },
];

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1-Click Presentation Demo Roles (Server-gated for Staging / Presentations)
  const [demoRoles, setDemoRoles] = useState<DemoRole[]>(DEFAULT_DEMO_ROLES);
  const [demoLoggingInRole, setDemoLoggingInRole] = useState<string | null>(null);
  const [demoDisabled, setDemoDisabled] = useState<boolean>(false);

  // Live Database Accounts for Demo Login (Employees & Brands)
  const [quickAccounts, setQuickAccounts] = useState<{
    employees: QuickLoginAccount[];
    brands: QuickLoginAccount[];
  }>({ employees: [], brands: [] });
  const [selectedEmpId, setSelectedEmpId] = useState<string>('');
  const [selectedBrandId, setSelectedBrandId] = useState<string>('');
  const [isQuickLoggingIn, setIsQuickLoggingIn] = useState<boolean>(false);
  const [directoryTab, setDirectoryTab] = useState<'employees' | 'brands'>('employees');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.getDemoRoles()
      .then((roles) => {
        if (!active) return;
        if (roles && roles.length > 0) {
          setDemoRoles(roles);
        }
        setDemoDisabled(false);
      })
      .catch(() => {
        if (!active) return;
        // In production environment, server returns 403 Forbidden
        setDemoDisabled(true);
      });

    // Fetch dynamic database accounts (all available employees and brands)
    api.getQuickLoginAccounts()
      .then((data) => {
        if (!active) return;
        if (data) {
          const filteredEmps = (data.employees || []).filter(
            (e) =>
              !['EMP55', 'EMP56', 'EMP57', 'EMP001'].includes(e.employee_code || '') &&
              !['aditya@example.com', 'demo@example.com', 'rohit@example.com', 'botemp@email.com'].includes(e.email) &&
              !e.pod_name?.toLowerCase().includes('new pod')
          );
          const filteredBrands = (data.brands || []).filter(
            (b) => !b.name.toLowerCase().includes('new brand') && b.code !== 'NEW' && b.code !== 'TEST'
          );
          setQuickAccounts({ employees: filteredEmps, brands: filteredBrands });
          if (filteredEmps.length > 0) {
            const firstEmp = filteredEmps[0];
            setSelectedEmpId(firstEmp.id);
            setEmail(firstEmp.email);
            setPassword(firstEmp.password);
          }
        }
      })
      .catch((err) => {
        console.warn('Live directory accounts unavailable:', err);
      });

    return () => {
      active = false;
    };
  }, []);

  const handleSelectEmployee = (empId: string) => {
    setSelectedEmpId(empId);
    setSelectedBrandId('');
    const emp = quickAccounts.employees.find((e) => e.id === empId);
    if (emp) {
      setEmail(emp.email);
      setPassword(emp.password);
      setError(null);
    }
  };

  const handleSelectBrand = (brandId: string) => {
    setSelectedBrandId(brandId);
    setSelectedEmpId('');
    const b = quickAccounts.brands.find((x) => x.id === brandId);
    if (b) {
      setEmail(b.email);
      setPassword(b.password);
      setError(null);
    }
  };

  const handleCopy = (text: string, key: string) => {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }
  };

  const handleAutoLoginDirect = async (userEmail: string, userPass: string) => {
    try {
      setIsQuickLoggingIn(true);
      setError(null);
      const user = await api.login(userEmail, userPass);
      onLoginSuccess(user);
    } catch (err: any) {
      setError(err.message || 'Auto-login failed. Please check credentials.');
    } finally {
      setIsQuickLoggingIn(false);
    }
  };

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

  const handleDemoLogin = async (role: string) => {
    try {
      setDemoLoggingInRole(role);
      setError(null);
      const user = await api.demoLogin(role);
      onLoginSuccess(user);
    } catch (err: any) {
      setError(err.message || `Failed to authenticate as ${role}`);
    } finally {
      setDemoLoggingInRole(null);
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'ADMIN':
        return <Shield className="w-4 h-4 text-indigo-500" />;
      case 'OPERATIONS_MANAGER':
        return <Users className="w-4 h-4 text-purple-500" />;
      case 'POD_LEAD':
        return <Layers className="w-4 h-4 text-emerald-500" />;
      case 'BRAND_USER':
        return <Building2 className="w-4 h-4 text-amber-500" />;
      case 'EMPLOYEE':
        return <UserCheck className="w-4 h-4 text-cyan-500" />;
      default:
        return <Shield className="w-4 h-4 text-slate-500" />;
    }
  };

  const hasDirectoryAccounts = quickAccounts.employees.length > 0 || quickAccounts.brands.length > 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200/80 dark:border-slate-800 overflow-hidden my-6">
        {/* Header Branding */}
        <div className="p-8 pb-6 text-center flex flex-col items-center space-y-3 bg-gradient-to-b from-indigo-50/50 to-white dark:from-slate-800/40 dark:to-slate-900">
          <RosterIQLogo variant="full" size="xl" showTagline={true} />
        </div>

        {/* Form Body */}
        <div className="p-8 pt-2 space-y-6">
          {error && (
            <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs rounded-xl flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* 1-Click Presentation Demo Roles Section */}
          {!demoDisabled && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
                    Presentation Demo Access
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                    5 Staging Roles
                  </span>
                </div>
                <span className="text-[11px] text-slate-500 dark:text-slate-400">
                  Click any role to enter directly
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {demoRoles.map((r, idx) => {
                  const isCurrentLoggingIn = demoLoggingInRole === r.role;
                  const isFullWidth = idx === 0; // System Admin spans full width on sm

                  return (
                    <button
                      key={r.role}
                      type="button"
                      disabled={Boolean(demoLoggingInRole) || isQuickLoggingIn || loading}
                      onClick={() => handleDemoLogin(r.role)}
                      className={`group relative flex items-center justify-between p-3 rounded-xl border text-left transition-all cursor-pointer ${
                        isFullWidth ? 'sm:col-span-2' : ''
                      } ${
                        isCurrentLoggingIn
                          ? 'bg-indigo-50 dark:bg-indigo-950/50 border-indigo-500 dark:border-indigo-600 ring-2 ring-indigo-500/20'
                          : 'bg-slate-50/70 dark:bg-slate-950/50 border-slate-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-700 hover:bg-indigo-50/40 dark:hover:bg-indigo-950/30'
                      } disabled:opacity-50`}
                    >
                      <div className="flex items-center gap-3 min-w-0 pr-2">
                        <span className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shrink-0 group-hover:scale-105 transition-transform">
                          {getRoleIcon(r.role)}
                        </span>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="font-bold text-xs text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                              {r.name}
                            </span>
                          </div>
                          <p className="text-[10px] text-slate-500 dark:text-slate-400 line-clamp-1 mt-0.5">
                            {r.description}
                          </p>
                        </div>
                      </div>

                      <div className="shrink-0 pl-1 text-slate-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                        {isCurrentLoggingIn ? (
                          <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                        ) : (
                          <ArrowRight className="w-4 h-4 transform group-hover:translate-x-0.5 transition-transform" />
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Demo Brand & Employee Accounts Directory (Live Database Accounts) */}
          {hasDirectoryAccounts && (
            <div className="p-3.5 bg-slate-50 dark:bg-slate-950/40 rounded-xl border border-slate-200 dark:border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                    <KeyRound className="w-3.5 h-3.5 text-indigo-500" />
                    Demo Accounts Directory
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                    Live Accounts
                  </span>
                </div>
                <div className="flex items-center gap-1 bg-white dark:bg-slate-900 p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 text-[10px] font-semibold">
                  <button
                    type="button"
                    onClick={() => {
                      setDirectoryTab('employees');
                      if (quickAccounts.employees.length > 0) {
                        const target = selectedEmpId
                          ? quickAccounts.employees.find((e) => e.id === selectedEmpId) || quickAccounts.employees[0]
                          : quickAccounts.employees[0];
                        handleSelectEmployee(target.id);
                      }
                    }}
                    className={`px-2 py-0.5 rounded-md transition-all cursor-pointer flex items-center gap-1 ${
                      directoryTab === 'employees'
                        ? 'bg-indigo-600 text-white shadow-2xs'
                        : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    <UserCheck className="w-3 h-3" />
                    <span>Employees ({quickAccounts.employees.length})</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setDirectoryTab('brands');
                      if (quickAccounts.brands.length > 0) {
                        const target = selectedBrandId
                          ? quickAccounts.brands.find((b) => b.id === selectedBrandId) || quickAccounts.brands[0]
                          : quickAccounts.brands[0];
                        handleSelectBrand(target.id);
                      }
                    }}
                    className={`px-2 py-0.5 rounded-md transition-all cursor-pointer flex items-center gap-1 ${
                      directoryTab === 'brands'
                        ? 'bg-amber-600 text-white shadow-2xs'
                        : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    <Building2 className="w-3 h-3" />
                    <span>Brands ({quickAccounts.brands.length})</span>
                  </button>
                </div>
              </div>

              {directoryTab === 'employees' ? (
                <div className="space-y-2">
                  <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400">
                    Select an employee account to autofill & log in:
                  </label>
                  <select
                    value={selectedEmpId}
                    onChange={(e) => handleSelectEmployee(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-900 dark:text-white font-medium focus:outline-hidden focus:border-indigo-500 cursor-pointer shadow-2xs"
                  >
                    <option value="">
                      -- Choose an Employee ({quickAccounts.employees.length} available) --
                    </option>
                    {quickAccounts.employees.map((emp) => (
                      <option key={emp.id} value={emp.id}>
                        {emp.name} ({emp.employee_code || 'EMP'}) · {emp.email} · [Pass: {emp.password}] · {emp.pod_name || 'Pod'}
                      </option>
                    ))}
                  </select>

                  {/* Selected Employee Preview Card */}
                  {selectedEmpId && (
                    (() => {
                      const emp = quickAccounts.employees.find((e) => e.id === selectedEmpId);
                      if (!emp) return null;
                      return (
                        <div className="p-3 bg-white dark:bg-slate-900 rounded-xl border border-indigo-200 dark:border-indigo-900/60 shadow-xs space-y-2.5 animate-in fade-in duration-150">
                          <div className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-900 dark:text-white text-xs">
                                {emp.name}
                              </span>
                              <span className="font-mono text-[10px] text-slate-400">
                                ({emp.employee_code})
                              </span>
                            </div>
                            <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                              {emp.pod_name || 'Assigned Pod'}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 text-[11px] bg-slate-50 dark:bg-slate-950/50 p-2 rounded-lg border border-slate-100 dark:border-slate-800 font-mono">
                            <div className="flex items-center justify-between pr-1 min-w-0">
                              <div className="min-w-0">
                                <span className="text-slate-400 block text-[9px] uppercase font-sans font-bold">Email</span>
                                <span className="text-indigo-600 dark:text-indigo-400 truncate block text-[10px]">{emp.email}</span>
                              </div>
                              <button
                                type="button"
                                onClick={() => handleCopy(emp.email, `emp-email-${emp.id}`)}
                                title="Copy Email"
                                className="p-1 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded transition-colors cursor-pointer shrink-0 ml-1"
                              >
                                {copiedKey === `emp-email-${emp.id}` ? (
                                  <Check className="w-3 h-3 text-emerald-500" />
                                ) : (
                                  <Copy className="w-3 h-3" />
                                )}
                              </button>
                            </div>
                            <div className="flex items-center justify-between pr-1 min-w-0">
                              <div className="min-w-0">
                                <span className="text-slate-400 block text-[9px] uppercase font-sans font-bold">Password</span>
                                <span className="text-emerald-600 dark:text-emerald-400 font-bold block text-[10px]">{emp.password}</span>
                              </div>
                              <button
                                type="button"
                                onClick={() => handleCopy(emp.password, `emp-pass-${emp.id}`)}
                                title="Copy Password"
                                className="p-1 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded transition-colors cursor-pointer shrink-0 ml-1"
                              >
                                {copiedKey === `emp-pass-${emp.id}` ? (
                                  <Check className="w-3 h-3 text-emerald-500" />
                                ) : (
                                  <Copy className="w-3 h-3" />
                                )}
                              </button>
                            </div>
                          </div>

                          <button
                            type="button"
                            disabled={isQuickLoggingIn || loading || Boolean(demoLoggingInRole)}
                            onClick={() => handleAutoLoginDirect(emp.email, emp.password)}
                            className="w-full flex items-center justify-center gap-1.5 py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
                          >
                            {isQuickLoggingIn ? (
                              <>
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                <span>Signing In...</span>
                              </>
                            ) : (
                              <>
                                <Zap className="w-3.5 h-3.5 text-amber-300" />
                                <span>Auto-Login as {emp.name}</span>
                              </>
                            )}
                          </button>
                        </div>
                      );
                    })()
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400">
                    Select a brand user account to autofill & log in:
                  </label>
                  <select
                    value={selectedBrandId}
                    onChange={(e) => handleSelectBrand(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-900 dark:text-white font-medium focus:outline-hidden focus:border-amber-500 cursor-pointer shadow-2xs"
                  >
                    <option value="">
                      -- Choose a Brand User ({quickAccounts.brands.length} available) --
                    </option>
                    {quickAccounts.brands.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name} ({b.code}) · {b.email} · [Pass: {b.password}]
                      </option>
                    ))}
                  </select>

                  {/* Selected Brand Preview Card */}
                  {selectedBrandId && (
                    (() => {
                      const b = quickAccounts.brands.find((x) => x.id === selectedBrandId);
                      if (!b) return null;
                      return (
                        <div className="p-3 bg-white dark:bg-slate-900 rounded-xl border border-amber-200 dark:border-amber-900/60 shadow-xs space-y-2.5 animate-in fade-in duration-150">
                          <div className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-900 dark:text-white text-xs">
                                {b.name}
                              </span>
                              <span className="font-mono text-[10px] text-slate-400">
                                ({b.code})
                              </span>
                            </div>
                            <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                              Brand User
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 text-[11px] bg-slate-50 dark:bg-slate-950/50 p-2 rounded-lg border border-slate-100 dark:border-slate-800 font-mono">
                            <div className="flex items-center justify-between pr-1 min-w-0">
                              <div className="min-w-0">
                                <span className="text-slate-400 block text-[9px] uppercase font-sans font-bold">Email</span>
                                <span className="text-amber-600 dark:text-amber-400 truncate block text-[10px]">{b.email}</span>
                              </div>
                              <button
                                type="button"
                                onClick={() => handleCopy(b.email, `brand-email-${b.id}`)}
                                title="Copy Email"
                                className="p-1 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded transition-colors cursor-pointer shrink-0 ml-1"
                              >
                                {copiedKey === `brand-email-${b.id}` ? (
                                  <Check className="w-3 h-3 text-emerald-500" />
                                ) : (
                                  <Copy className="w-3 h-3" />
                                )}
                              </button>
                            </div>
                            <div className="flex items-center justify-between pr-1 min-w-0">
                              <div className="min-w-0">
                                <span className="text-slate-400 block text-[9px] uppercase font-sans font-bold">Password</span>
                                <span className="text-emerald-600 dark:text-emerald-400 font-bold block text-[10px]">{b.password}</span>
                              </div>
                              <button
                                type="button"
                                onClick={() => handleCopy(b.password, `brand-pass-${b.id}`)}
                                title="Copy Password"
                                className="p-1 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded transition-colors cursor-pointer shrink-0 ml-1"
                              >
                                {copiedKey === `brand-pass-${b.id}` ? (
                                  <Check className="w-3 h-3 text-emerald-500" />
                                ) : (
                                  <Copy className="w-3 h-3" />
                                )}
                              </button>
                            </div>
                          </div>

                          <button
                            type="button"
                            disabled={isQuickLoggingIn || loading || Boolean(demoLoggingInRole)}
                            onClick={() => handleAutoLoginDirect(b.email, b.password)}
                            className="w-full flex items-center justify-center gap-1.5 py-2 px-3 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
                          >
                            {isQuickLoggingIn ? (
                              <>
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                <span>Signing In...</span>
                              </>
                            ) : (
                              <>
                                <Zap className="w-3.5 h-3.5 text-white" />
                                <span>Auto-Login as {b.name}</span>
                              </>
                            )}
                          </button>
                        </div>
                      );
                    })()
                  )}
                </div>
              )}
            </div>
          )}

          {/* Divider */}
          <div className="relative flex items-center justify-center">
            <div className="border-t border-slate-200 dark:border-slate-800 w-full" />
            <span className="bg-white dark:bg-slate-900 px-3 text-[10px] uppercase font-bold tracking-wider text-slate-400">
              Or Sign In With Password
            </span>
          </div>

          {/* Standard Email & Password Form */}
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
              disabled={loading || Boolean(demoLoggingInRole) || isQuickLoggingIn}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-xs shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
            >
              <span>{loading ? 'Authenticating...' : 'Sign In to Workspace'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
