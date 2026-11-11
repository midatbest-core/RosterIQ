import React from 'react';
import {
  LayoutDashboard,
  Users,
  Network,
  CalendarOff,
  Briefcase,
  GitFork,
  Sliders,
  Calendar,
  Sparkles,
  ShieldAlert,
  ArrowRightLeft,
  History,
  FileText,
  ChevronLeft,
  ChevronRight,
  BarChart3,
} from 'lucide-react';

export type NavTab =
  | 'dashboard'
  | 'analytics'
  | 'requests'
  | 'roster'
  | 'conflicts'
  | 'allocation-log'
  | 'employees'
  | 'pods'
  | 'leaves'
  | 'brands'
  | 'assignments'
  | 'rules'
  | 'history';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  conflictCount?: number;
  onOpenGenerateModal?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  isCollapsed,
  onToggleCollapse,
  conflictCount = 0,
  onOpenGenerateModal,
}) => {
  const sections = [
    {
      group: 'OVERVIEW',
      items: [
        { id: 'dashboard' as NavTab, label: 'Dashboard', icon: LayoutDashboard },
        { id: 'analytics' as NavTab, label: 'Workforce Analytics', icon: BarChart3 },
      ],
    },
    {
      group: 'SCHEDULING',
      items: [
        { id: 'requests' as NavTab, label: 'Requests & Approvals', icon: FileText },
        { id: 'roster' as NavTab, label: 'Roster Calendar', icon: Calendar },
        {
          id: 'conflicts' as NavTab,
          label: 'Conflicts & Coverage',
          icon: ShieldAlert,
          badge: conflictCount > 0 ? conflictCount : undefined,
          badgeVariant: 'rose',
        },
        { id: 'allocation-log' as NavTab, label: 'Dynamic Allocation Log', icon: ArrowRightLeft },
      ],
    },
    {
      group: 'WORKFORCE',
      items: [
        { id: 'employees' as NavTab, label: 'Employees', icon: Users },
        { id: 'pods' as NavTab, label: 'Pods Directory', icon: Network },
        { id: 'leaves' as NavTab, label: 'Availability & Leave', icon: CalendarOff },
      ],
    },
    {
      group: 'OPERATIONS',
      items: [
        { id: 'brands' as NavTab, label: 'Brands & Processes', icon: Briefcase },
        { id: 'assignments' as NavTab, label: 'Primary Assignments', icon: GitFork },
        { id: 'rules' as NavTab, label: 'Operating Rules', icon: Sliders },
      ],
    },
    {
      group: 'MANAGEMENT',
      items: [
        { id: 'history' as NavTab, label: 'Roster History & Versions', icon: History },
      ],
    },
  ];

  return (
    <aside
      className={`h-screen bg-slate-900 border-r border-slate-800 flex flex-col transition-all duration-300 z-40 select-none ${
        isCollapsed ? 'w-18' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800/80">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white font-bold shadow-md shadow-indigo-900/30 shrink-0">
            <Calendar className="w-5 h-5" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-sm tracking-tight text-white">RosterIQ</span>
                <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded-sm bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  WFM
                </span>
              </div>
              <span className="text-[11px] text-slate-400 font-medium">Enterprise Suite</span>
            </div>
          )}
        </div>
        <button
          onClick={onToggleCollapse}
          className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Quick Action: Generate Roster */}
      {!isCollapsed && onOpenGenerateModal && (
        <div className="p-3 border-b border-slate-800/60">
          <button
            onClick={onOpenGenerateModal}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow-sm shadow-indigo-600/30 transition-all cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Generate Roster</span>
          </button>
        </div>
      )}

      {/* Navigation Sections */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-5">
        {sections.map((section) => (
          <div key={section.group} className="space-y-1">
            {!isCollapsed && (
              <p className="px-3 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                {section.group}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectTab(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                      isActive
                        ? 'bg-indigo-600 text-white font-semibold shadow-xs shadow-indigo-900/50'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`}
                    title={isCollapsed ? item.label : undefined}
                  >
                    <Icon
                      className={`w-4 h-4 shrink-0 ${
                        isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'
                      }`}
                    />
                    {!isCollapsed && (
                      <div className="flex-1 flex items-center justify-between text-left truncate">
                        <span className="truncate">{item.label}</span>
                        {item.badge !== undefined && (
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full ${
                              isActive
                                ? 'bg-white text-indigo-700'
                                : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            }`}
                          >
                            {item.badge}
                          </span>
                        )}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Footer System Status */}
      <div className="p-3 border-t border-slate-800 bg-slate-900/50">
        {!isCollapsed ? (
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Engine Online
            </span>
            <span className="font-mono text-[10px] text-slate-600">v1.2.0</span>
          </div>
        ) : (
          <div className="flex justify-center">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="Engine Online" />
          </div>
        )}
      </div>
    </aside>
  );
};

