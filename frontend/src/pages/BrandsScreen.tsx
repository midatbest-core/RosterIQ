import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Brand, ProcessItem, BrandProcess } from '../services/types';
import { Briefcase, Plus, Layers } from 'lucide-react';

export const BrandsScreen: React.FC = () => {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [processes, setProcesses] = useState<ProcessItem[]>([]);
  const [brandProcesses, setBrandProcesses] = useState<BrandProcess[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showAddBrand, setShowAddBrand] = useState(false);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');

  const [showAddBp, setShowAddBp] = useState(false);
  const [selectedBrandId, setSelectedBrandId] = useState('');
  const [selectedProcessId, setSelectedProcessId] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [bList, prList, bpList] = await Promise.all([
        api.getBrands(),
        api.getProcesses(),
        api.getBrandProcesses(),
      ]);
      setBrands(bList);
      setProcesses(prList);
      setBrandProcesses(bpList);
      if (bList.length > 0 && !selectedBrandId) setSelectedBrandId(bList[0].id);
      if (prList.length > 0 && !selectedProcessId) setSelectedProcessId(prList[0].id);
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
      await api.createBrand(code, name);
      setShowAddBrand(false);
      setCode('');
      setName('');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to create brand');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBp = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await api.createBrandProcess(selectedBrandId, selectedProcessId);
      setShowAddBp(false);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to attach process');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Briefcase className="w-6 h-6 text-indigo-600" />
          <div>
            <h1 className="text-xl font-bold text-slate-900">Brands & Operational Processes</h1>
            <p className="text-xs text-slate-500">
              Manage D2C client brands, process associations, and operating pattern calendars
            </p>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => setShowAddBrand(true)}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white font-medium text-sm rounded-lg flex items-center gap-2 shadow-sm transition"
          >
            <Plus className="w-4 h-4" /> Add Brand
          </button>
          <button
            onClick={() => setShowAddBp(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded-lg flex items-center gap-2 shadow-sm transition"
          >
            <Layers className="w-4 h-4" /> Attach Process
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 text-sm rounded-xl">
          {error}
        </div>
      )}

      {/* Grid of Active Brands */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {brands.map((b) => {
          const attached = brandProcesses.filter((bp) => bp.brand_id === b.id);
          return (
            <div
              key={b.id}
              className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3 hover:border-indigo-300 transition"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-base text-slate-900">{b.name}</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                  {b.code}
                </span>
              </div>

              <div className="border-t border-slate-100 pt-3 space-y-2">
                <span className="text-xs font-semibold text-slate-600 block">
                  Active Processes ({attached.length})
                </span>
                {attached.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No processes attached yet.</p>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {attached.map((bp) => {
                      const proc = processes.find((p) => p.id === bp.process_id);
                      return (
                        <span
                          key={bp.id}
                          className="px-2 py-1 bg-indigo-50 border border-indigo-200 text-indigo-800 rounded text-[11px] font-medium"
                        >
                          {proc?.name || 'Unknown'}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Brand Modal */}
      {showAddBrand && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900">Add New Brand</h2>
            <form onSubmit={handleCreateBrand} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Brand Code</label>
                <input
                  type="text"
                  placeholder="ACME"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm uppercase"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Brand Name</label>
                <input
                  type="text"
                  placeholder="Acme D2C Organics"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  required
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddBrand(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 text-sm font-medium rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg"
                >
                  Save Brand
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Attach Process Modal */}
      {showAddBp && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900">Attach Process to Brand</h2>
            <form onSubmit={handleCreateBp} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Brand</label>
                <select
                  value={selectedBrandId}
                  onChange={(e) => setSelectedBrandId(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
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
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  {processes.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddBp(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 text-sm font-medium rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg"
                >
                  Attach & Create Default Operating Pattern
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

