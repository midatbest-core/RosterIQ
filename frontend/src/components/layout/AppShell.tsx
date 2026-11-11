import React, { useState } from 'react';
import { Sidebar, NavTab } from './Sidebar';
import { Topbar } from './Topbar';
import { User, RosterSummary } from '../../services/types';

interface AppShellProps {
  currentUser: User | null;
  onLogout: () => void;
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  rosters: RosterSummary[];
  selectedRosterId: string;
  onSelectRosterId: (id: string) => void;
  conflictCount: number;
  onOpenGenerateModal: () => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentUser,
  onLogout,
  activeTab,
  onSelectTab,
  rosters,
  selectedRosterId,
  onSelectRosterId,
  conflictCount,
  onOpenGenerateModal,
  searchQuery,
  onSearchChange,
  children,
}) => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 font-sans text-slate-800 antialiased">
      {/* Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={onSelectTab}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        conflictCount={conflictCount}
        onOpenGenerateModal={onOpenGenerateModal}
      />

      {/* Main Column */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <Topbar
          activeTab={activeTab}
          currentUser={currentUser}
          onLogout={onLogout}
          rosters={rosters}
          selectedRosterId={selectedRosterId}
          onSelectRosterId={onSelectRosterId}
          conflictCount={conflictCount}
          onOpenConflicts={() => onSelectTab('conflicts')}
          searchQuery={searchQuery}
          onSearchChange={onSearchChange}
        />

        {/* Dynamic Page Content */}
        <main className="flex-1 overflow-y-auto p-6 min-w-0">
          <div className="max-w-7xl mx-auto space-y-6">{children}</div>
        </main>
      </div>
    </div>
  );
};

