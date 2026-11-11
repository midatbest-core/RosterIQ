import React from 'react';
import {
  Search,
  Bell,
  ShieldAlert,
  LogOut,
  Calendar,
  Layers,
  ChevronDown,
  User as UserIcon,
} from 'lucide-react';
import { User, RosterSummary } from '../../services/types';
import { NavTab } from './Sidebar';

interface TopbarProps {
  activeTab: NavTab;
  currentUser: User | null;
  onLogout: () => void;
  rosters: RosterSummary[];
  selectedRosterId: string;
  onSelectRosterId: (id: string) => void;
  conflictCount: number;
  onOpenConflicts: () => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

export const Topbar: React.FC<TopbarProps> = ({
  activeTab,
  currentUser,
  onLogout,
  rosters,
  selectedRosterId,
  onSelectRosterId,
  conflictCount,
  onOpenConflicts,
  searchQuery,
  onSearchChange,
}) => {
  const getTabBreadcrumb = (tab: NavTab) => {
    switch (tab) {
      case 'dashboard':
        return { section: 'Overview', title: 'Operational Dashboard' };
      case 'analytics':
        return { section: 'Overview', title: 'Workforce Capacity & Pod Analytics' };
      case 'roster':
        return { section: 'Scheduling', title: 'Roster Calendar Workspace' };
      case 'conflicts':
        return { section: 'Scheduling', title: 'Conflicts & Coverage Exceptions' };
      case 'allocation-log':
        return { section: 'Scheduling', title: 'Dynamic Allocation & Reassignment Log' };
      case 'employees':
        return { section: 'Workforce', title: 'Employee Directory' };
      case 'pods':
        return { section: 'Workforce', title: 'Pods & Pod Leads' };
      case 'leaves':
        return { section: 'Workforce', title: 'Availability & Approved Leaves' };
      case 'brands':
        return { section: 'Operations', title: 'Brands & Processes' };
      case 'assignments':
        return { section: 'Operations', title: 'Primary Process Assignments' };
      case 'rules':
        return { section: 'Operations', title: 'Operating Patterns & Holiday Rules' };
      case 'history':
        return { section: 'Management', title: 'Roster Versioning & Audit History' };
      default:
        return { section: 'RosterIQ', title: 'Workforce Management' };
    }
  };

  const breadcrumb = getTabBreadcrumb(activeTab);
  const currentRoster = rosters.find((r) => r.id === selectedRosterId);

  return (
    <header className="h-16 bg-white border-b border-slate-200/80 px-6 flex items-center justify-between z-30 shrink-0">
      {/* Breadcrumb & Title */}
      <div className="flex flex-col">
        <div className="flex items-center gap-2 text-[11px] font-medium text-slate-400">
          <span>RosterIQ</span>
          <span>/</span>
          <span>{breadcrumb.section}</span>
        </div>
        <h1 className="text-base font-bold text-slate-900 tracking-tight">{breadcrumb.title}</h1>
      </div>

      {/* Center: Search & Active Roster Picker */}
      <div className="flex items-center gap-3">
        {/* Global Search */}
        <div className="relative w-64 hidden md:block">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search employees, brands..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-8.5 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder:text-slate-400 focus:outline-hidden focus:border-indigo-500 focus:bg-white transition-all"
          />
        </div>

        {/* Active Roster Selector */}
        {rosters.length > 0 && (
          <div className="relative flex items-center">
            <select
              value={selectedRosterId}
              onChange={(e) => onSelectRosterId(e.target.value)}
              className="appearance-none pl-8 pr-8 py-1.5 bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700 rounded-lg focus:outline-hidden focus:border-indigo-500 cursor-pointer shadow-2xs hover:bg-slate-100 transition-all"
            >
              {rosters.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} (v{r.version}) — {r.status}
                </option>
              ))}
            </select>
            <Calendar className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 pointer-events-none" />
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 pointer-events-none" />
          </div>
        )}
      </div>

      {/* Right Controls: Conflict Pill & User Profile */}
      <div className="flex items-center gap-4">
        {/* Conflict Quick Alert */}
        {conflictCount > 0 && (
          <button
            onClick={onOpenConflicts}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 transition-colors text-xs font-semibold cursor-pointer"
            title="Review active roster conflicts"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-rose-600 animate-pulse" />
            <span>{conflictCount} Conflicts</span>
          </button>
        )}

        {/* User Profile */}
        <div className="flex items-center gap-3 pl-2 border-l border-slate-200">
          <div className="flex flex-col text-right hidden sm:flex">
            <span className="text-xs font-semibold text-slate-800 leading-tight">
              {currentUser?.email || 'Admin User'}
            </span>
            <div className="flex items-center justify-end gap-1 mt-0.5">
              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-xs bg-indigo-50 text-indigo-700 border border-indigo-200 uppercase">
                {currentUser?.role === 'ADMIN' ? 'Administrator' : 'Operations Manager'}
              </span>
            </div>
          </div>
          <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 font-semibold text-xs">
            <UserIcon className="w-4 h-4" />
          </div>
          <button
            onClick={onLogout}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};

