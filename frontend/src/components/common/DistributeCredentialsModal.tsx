import React, { useState } from 'react';
import { Modal } from './Modal';
import { CreatedCredentials } from '../../services/types';
import { KeyRound, Copy, Check, ShieldCheck, Mail, Lock, User, Layers, CheckCircle2 } from 'lucide-react';

interface DistributeCredentialsModalProps {
  isOpen: boolean;
  onClose: () => void;
  credentials: CreatedCredentials | null;
}

export const DistributeCredentialsModal: React.FC<DistributeCredentialsModalProps> = ({
  isOpen,
  onClose,
  credentials,
}) => {
  const [copied, setCopied] = useState(false);

  if (!credentials) return null;

  const handleCopy = () => {
    const loginUrl = window.location.origin;
    const textToCopy = `=== RosterIQ Workspace Credentials ===
Name: ${credentials.name}
Role: ${credentials.role}
Email: ${credentials.email}
Temporary Password: ${credentials.temporaryPassword}
Login URL: ${loginUrl}
======================================`;

    navigator.clipboard.writeText(textToCopy).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Login Credentials Ready for Distribution"
      subtitle="Account provisioned successfully. Share these credentials with the user for workspace access."
      maxWidth="md"
    >
      <div className="space-y-4 p-1">
        {/* Success Banner */}
        <div className="p-3.5 bg-emerald-50 border border-emerald-200/90 rounded-xl flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-emerald-900">
              New Account Active in Database
            </h4>
            <p className="text-[11px] text-emerald-700 mt-0.5 leading-relaxed">
              Authentication credentials have been configured. The user can immediately log in from the login page or using the Employee Quick Login dropdown.
            </p>
          </div>
        </div>

        {/* Credentials Card */}
        <div className="bg-slate-50 rounded-xl border border-slate-200/80 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200/60 pb-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-indigo-500" />
              Account Credentials
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">
              {credentials.role}
            </span>
          </div>

          <div className="grid grid-cols-1 gap-2 text-xs">
            {/* User Name */}
            <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200/60">
              <span className="text-slate-500 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-slate-400" />
                Account Name:
              </span>
              <span className="font-semibold text-slate-900">{credentials.name}</span>
            </div>

            {/* Email */}
            <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200/60">
              <span className="text-slate-500 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-slate-400" />
                Login Email:
              </span>
              <span className="font-mono font-bold text-indigo-600">{credentials.email}</span>
            </div>

            {/* Password */}
            <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200/60">
              <span className="text-slate-500 flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-slate-400" />
                Temporary Password:
              </span>
              <span className="font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                {credentials.temporaryPassword}
              </span>
            </div>

            {/* Pod if available */}
            {credentials.podName && (
              <div className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200/60">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-slate-400" />
                  Assigned Pod:
                </span>
                <span className="font-medium text-slate-700">{credentials.podName}</span>
              </div>
            )}
          </div>
        </div>

        {/* Buttons */}
        <div className="pt-2 flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="flex-1 flex items-center justify-center gap-2 py-2 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>Copied to Clipboard!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-slate-300" />
                <span>Copy Credentials to Distribute</span>
              </>
            )}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="py-2 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </Modal>
  );
};
