import React from 'react';
import { Modal } from './Modal';
import { ValidationErrorDetail } from '../../services/types';
import { AlertTriangle, AlertCircle, ArrowRight, X } from 'lucide-react';

interface ValidationErrorPopupModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  entityName?: string;
  errors: ValidationErrorDetail[];
  fallbackMessage?: string;
}

export const ValidationErrorPopupModal: React.FC<ValidationErrorPopupModalProps> = ({
  isOpen,
  onClose,
  title = 'Invalid Input Data',
  subtitle = 'The server rejected the request because one or more fields contain invalid data.',
  entityName = 'Record',
  errors,
  fallbackMessage,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      maxWidth="md"
    >
      <div className="space-y-4 p-1">
        {/* Banner Alert */}
        <div className="p-3.5 bg-rose-50 border border-rose-200/90 rounded-xl flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-rose-100 text-rose-700 flex items-center justify-center shrink-0">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-rose-900">
              Please correct the highlighted inputs
            </h4>
            <p className="text-[11px] text-rose-700 mt-0.5 leading-relaxed">
              Creation of {entityName} failed because the provided values do not meet operational constraints or format specifications.
            </p>
          </div>
        </div>

        {/* Detailed Breakdown of Errors */}
        <div className="space-y-2.5">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Incorrect Fields ({errors.length > 0 ? errors.length : 1})
          </span>

          {errors.length > 0 ? (
            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {errors.map((err, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 hover:border-rose-300 transition-colors space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
                      {err.fieldLabel || err.field}
                    </span>
                    <span className="font-mono text-[10px] text-slate-400">
                      Field: {err.field}
                    </span>
                  </div>

                  <p className="text-xs text-slate-800 font-medium flex items-start gap-1.5 pt-0.5">
                    <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0 mt-0.5" />
                    <span>{err.reason}</span>
                  </p>

                  {err.providedValue !== undefined && err.providedValue !== '' && (
                    <div className="text-[11px] text-slate-500 bg-white px-2 py-1 rounded border border-slate-200/60 font-mono truncate">
                      <span className="text-slate-400">Value received:</span> "{String(err.providedValue)}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-700 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{fallbackMessage || 'The request contains invalid data. Please verify all fields and try again.'}</span>
            </div>
          )}
        </div>

        {/* Action Button */}
        <div className="pt-2 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="w-full flex items-center justify-center gap-2 py-2 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <span>Review & Correct Inputs</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </Modal>
  );
};
