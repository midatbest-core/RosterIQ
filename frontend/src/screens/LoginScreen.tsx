import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { User, PresentationDemoAccount } from '../services/types';
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
  ChevronDown,
  ChevronUp,
  KeyRound,
  Copy,
  Check,
  Sparkles,
} from 'lucide-react';

interface LoginScreenProps {
  onLoginSuccess: (user: User) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Presentation Demo Accounts (Staging / Development only; server-gated)
  const [presentationAccounts, setPresentationAccounts] = useState<PresentationDemoAccount[]>([]);
  const [showPresentationAccounts, setShowPresentationAccounts] = useState<boolean>(true);
  const [demoLoading, setDemoLoading] = useState<boolean>(true);
  const [demoDisabled, setDemoDisabled] = useState<boolean>(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.getPresentationDemoAccounts()
      .then((accounts) => {
        if (!active) return;
        setPresentationAccounts(accounts);
        setDemoDisabled(false);
      })
      .catch((err) => {
        if (!active) return;
        // In production or when flag is disabled, server returns 403 Forbidden
        setPresentationAccounts([]);
        setDemoDisabled(true);
        if (import.meta.env.DEV) {
          console.log('Presentation demo credentials unavailable:', err.message);
        }
      })
      .finally(() => {
        if (active) setDemoLoading(false);
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

  const handleCopy = (text: string, key: string) => {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => {
        setCopiedKey(null);
      }, 2000);
    }
  };

  const handleUseAccount = (acc: PresentationDemoAccount) => {
    setEmail(acc.email);
    setPassword(acc.password);
    setError(null);
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'ADMIN':
        return <Shield className="w-3.5 h-3.5 text-indigo-500 shrink-0" />;
      case 'OPERATIONS_MANAGER':
        return <Users className="w-3.5 h-3.5 text-purple-500 shrink-0" />;
      case 'POD_LEAD':
        return <Layers className="w-3.5 h-3.5 text-emerald-500 shrink-0" />;
      case 'BRAND_USER':
        return <Building2 className="w-3.5 h-3.5 text-amber-500 shrink-0" />;
      case 'EMPLOYEE':
        return <UserCheck className="w-3.5 h-3.5 text-cyan-500 shrink-0" />;
      default:
        return <KeyRound className="w-3.5 h-3.5 text-slate-500 shrink-0" />;
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

          {/* Presentation Demo Accounts Section (Server-gated for Staging / Presentations) */}
          {!demoDisabled && (
            <div className="pt-4 border-t border-slate-200/80 dark:border-slate-800/80 space-y-3">
              <button
                type="button"
                onClick={() => setShowPresentationAccounts(!showPresentationAccounts)}
                className="w-full flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-800 transition-all text-left cursor-pointer group"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-indigo-500/10 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400">
                    <KeyRound className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-slate-900 dark:text-white">
                        Presentation Demo Accounts
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 flex items-center gap-1">
                        <Sparkles className="w-2.5 h-2.5" /> 5 Verified Roles
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-500 dark:text-slate-400">
                      Staging test credentials for evaluator presentations & walkthroughs
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1 text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200 transition-colors">
                  <span className="text-[11px] font-medium hidden sm:inline">
                    {showPresentationAccounts ? 'Hide' : 'Show'}
                  </span>
                  {showPresentationAccounts ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </div>
              </button>

              {/* Expandable Demo Accounts Cards */}
              {showPresentationAccounts && (
                <div className="space-y-2 pt-1 animate-in fade-in duration-200">
                  {demoLoading && (
                    <div className="p-4 text-center text-xs text-slate-500 dark:text-slate-400">
                      Loading presentation credentials from staging server...
                    </div>
                  )}

                  {presentationAccounts.map((acc) => {
                    const isSelected = email === acc.email;
                    const emailCopyKey = `${acc.role}-email`;
                    const pwdCopyKey = `${acc.role}-pwd`;

                    return (
                      <div
                        key={acc.role}
                        className={`p-3 rounded-xl border transition-all ${
                          isSelected
                            ? 'bg-indigo-50/70 dark:bg-indigo-950/40 border-indigo-300 dark:border-indigo-700 shadow-xs'
                            : 'bg-slate-50/70 dark:bg-slate-950/40 border-slate-200/80 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                        }`}
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center gap-2.5">
                            <span className="p-1.5 rounded-lg bg-slate-200/60 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                              {getRoleIcon(acc.role)}
                            </span>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-xs text-slate-900 dark:text-white">
                                  {acc.role_name}
                                </span>
                                <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 px-1.5 py-0.2 bg-slate-200/50 dark:bg-slate-800 rounded">
                                  {acc.role}
                                </span>
                              </div>
                              <p className="text-[10px] text-slate-500 dark:text-slate-400 line-clamp-1">
                                {acc.description}
                              </p>
                            </div>
                          </div>

                          <button
                            type="button"
                            onClick={() => handleUseAccount(acc)}
                            className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition-colors cursor-pointer shrink-0"
                          >
                            <span>Use Account</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </div>

                        {/* Credentials Fields with Copy Buttons */}
                        <div className="mt-2.5 pt-2 border-t border-slate-200/60 dark:border-slate-800/80 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                          {/* Email Field with Copy */}
                          <div className="flex items-center justify-between bg-white dark:bg-slate-900 px-2.5 py-1.5 rounded-lg border border-slate-200/60 dark:border-slate-800">
                            <div className="flex items-center gap-1.5 min-w-0">
                              <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                              <span className="text-[11px] font-mono text-slate-700 dark:text-slate-300 truncate">
                                {acc.email}
                              </span>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleCopy(acc.email, emailCopyKey)}
                              title="Copy Email"
                              className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-white rounded transition-colors cursor-pointer shrink-0"
                            >
                              {copiedKey === emailCopyKey ? (
                                <Check className="w-3.5 h-3.5 text-emerald-500" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>

                          {/* Password Field with Copy */}
                          <div className="flex items-center justify-between bg-white dark:bg-slate-900 px-2.5 py-1.5 rounded-lg border border-slate-200/60 dark:border-slate-800">
                            <div className="flex items-center gap-1.5 min-w-0">
                              <Lock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                              <span className="text-[11px] font-mono text-slate-700 dark:text-slate-300 truncate tracking-wide">
                                {acc.password}
                              </span>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleCopy(acc.password, pwdCopyKey)}
                              title="Copy Password"
                              className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-white rounded transition-colors cursor-pointer shrink-0"
                            >
                              {copiedKey === pwdCopyKey ? (
                                <Check className="w-3.5 h-3.5 text-emerald-500" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginScreen;
