import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { User, DemoRole } from '../services/types';
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
  UserCheck,
  Sparkles,
  Loader2,
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
    description: 'Pod Alpha team scheduling, unavailability logging & approvals',
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

    return () => {
      active = false;
    };
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
        <div className="p-8 pt-2 space-y-6">
          {error && (
            <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:rose-900 text-rose-700 dark:text-rose-300 text-xs rounded-xl flex items-start gap-2">
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
                      disabled={Boolean(demoLoggingInRole) || loading}
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
              disabled={loading || Boolean(demoLoggingInRole)}
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
