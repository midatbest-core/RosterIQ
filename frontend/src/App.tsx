import React, { useState, useEffect } from 'react';
import { api } from './services/api';
import { User, RosterSummary } from './services/types';
import { AppShell } from './components/layout/AppShell';
import { NavTab } from './components/layout/Sidebar';
import { DashboardScreen } from './screens/DashboardScreen';
import { AnalyticsScreen } from './screens/AnalyticsScreen';
import { RosterCalendarScreen } from './screens/RosterCalendarScreen';
import { ConflictsScreen } from './screens/ConflictsScreen';
import { AllocationLogScreen } from './screens/AllocationLogScreen';
import { WorkforceScreen } from './screens/WorkforceScreen';
import { OperationsScreen } from './screens/OperationsScreen';
import { AuditHistoryScreen } from './screens/AuditHistoryScreen';
import { LoginScreen } from './screens/LoginScreen';
import { BrandPortalScreen } from './screens/BrandPortalScreen';
import { EmployeePortalScreen } from './screens/EmployeePortalScreen';
import { RequestsCenterScreen } from './screens/RequestsCenterScreen';
import { GenerateRosterModal } from './components/roster/GenerateRosterModal';
import { NotificationBell } from './components/notifications/NotificationBell';
import { useNotifications } from './hooks/useNotifications';
import { RosterIQLogo } from './components/brand/RosterIQLogo';
import { Activity } from 'lucide-react';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [loading, setLoading] = useState(true);
  const [rosters, setRosters] = useState<RosterSummary[]>([]);
  const [selectedRosterId, setSelectedRosterId] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showGenerateModal, setShowGenerateModal] = useState(false);

  const {
    notifications,
    unreadCount,
    isConnected,
    markAsRead,
    deleteNotification,
  } = useNotifications(currentUser);

  useEffect(() => {
    checkAuth();
  }, []);

  // Multi-tab session synchronization: update current user or log out when another tab changes authentication state
  useEffect(() => {
    const handleStorageEvent = async (e: StorageEvent) => {
      if (e.key === 'rosteriq_auth_event' && e.newValue) {
        try {
          const evt = JSON.parse(e.newValue);
          if (evt.type === 'logout') {
            setCurrentUser(null);
            setSelectedRosterId('');
            setRosters([]);
          } else if (evt.type === 'login') {
            const freshUser = await api.getCurrentUser();
            if (freshUser) {
              setCurrentUser(freshUser);
              if (
                freshUser.role === 'ADMIN' ||
                freshUser.role === 'OPERATIONS_MANAGER' ||
                freshUser.role === 'POD_LEAD'
              ) {
                await loadRosters();
              }
            }
          }
        } catch {}
      }
    };

    window.addEventListener('storage', handleStorageEvent);
    return () => window.removeEventListener('storage', handleStorageEvent);
  }, []);

  useEffect(() => {
    if (currentUser?.role === 'POD_LEAD') {
      const allowedTabs: NavTab[] = ['roster', 'my-schedule', 'analytics', 'conflicts', 'employees', 'requests'];
      if (!allowedTabs.includes(activeTab)) {
        setActiveTab('roster');
      }
    }
  }, [currentUser, activeTab]);

  const checkAuth = async () => {
    try {
      setLoading(true);
      const user = await api.getCurrentUser();
      setCurrentUser(user);
      await loadRosters();
    } catch {
      setCurrentUser(null);
    } finally {
      setLoading(false);
    }
  };

  const loadRosters = async () => {
    try {
      const list = await api.getRosters();
      setRosters(list);
      if (list.length > 0 && !selectedRosterId) {
        setSelectedRosterId(list[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load rosters:', err);
      // In multi-tab scenarios, another tab may have switched to a role that cannot view rosters (e.g. EMPLOYEE)
      if (
        err?.message?.includes('permission') ||
        err?.message?.includes('FORBIDDEN') ||
        err?.message?.includes('403')
      ) {
        try {
          const freshUser = await api.getCurrentUser();
          if (freshUser && freshUser.role !== currentUser?.role) {
            setCurrentUser(freshUser);
          }
        } catch {
          setCurrentUser(null);
        }
      }
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setCurrentUser(null);
      setSelectedRosterId('');
      setRosters([]);
    }
  };

  const currentRoster = rosters.find((r) => r.id === selectedRosterId) || rosters[0];
  const conflictCount = currentRoster ? currentRoster.hard_violations_count : 0;

  if (loading && !currentUser) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-white space-y-3">
        <div className="w-9 h-9 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs font-semibold text-slate-400">Initializing RosterIQ Workspace...</p>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <LoginScreen
        onLoginSuccess={async (user) => {
          setCurrentUser(user);
          await loadRosters();
        }}
      />
    );
  }

  // Brand User view
  if (currentUser.role === 'BRAND_USER') {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
        <header className="relative z-50 border-b border-slate-800 bg-slate-900/80 backdrop-blur px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <RosterIQLogo variant="full" size="md" showTagline={false} />
            <div className="h-5 w-px bg-slate-800" />
            <p className="text-xs text-slate-400 font-medium">Brand Partner Self-Service Portal</p>
          </div>
          <div className="flex items-center gap-4">
            <NotificationBell
              notifications={notifications}
              unreadCount={unreadCount}
              isConnected={isConnected}
              onMarkAsRead={markAsRead}
              onDelete={deleteNotification}
            />
            <div className="text-right">
              <p className="text-xs font-semibold text-white">{currentUser.email}</p>
              <p className="text-[11px] text-slate-400 capitalize">{currentUser.role.replace('_', ' ')}</p>
            </div>
            <button
              onClick={handleLogout}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-rose-400 border border-slate-700 transition-colors cursor-pointer"
            >
              Sign Out
            </button>
          </div>
        </header>
        <main className="flex-1">
          <BrandPortalScreen />
        </main>
      </div>
    );
  }

  // Employee User view
  if (currentUser.role === 'EMPLOYEE') {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
        <header className="relative z-50 border-b border-slate-800 bg-slate-900/80 backdrop-blur px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <RosterIQLogo variant="full" size="md" showTagline={false} />
            <div className="h-5 w-px bg-slate-800" />
            <p className="text-xs text-slate-400 font-medium">Employee Shift & Task Workspace</p>
          </div>
          <div className="flex items-center gap-4">
            <NotificationBell
              notifications={notifications}
              unreadCount={unreadCount}
              isConnected={isConnected}
              onMarkAsRead={markAsRead}
              onDelete={deleteNotification}
            />
            <div className="text-right">
              <p className="text-xs font-semibold text-white">{currentUser.email}</p>
              <p className="text-[11px] text-slate-400">Employee Workspace</p>
            </div>
            <button
              onClick={handleLogout}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-rose-400 border border-slate-700 transition-colors"
            >
              Sign Out
            </button>
          </div>
        </header>
        <main className="flex-1">
          <EmployeePortalScreen />
        </main>
      </div>
    );
  }

  return (
    <AppShell
      currentUser={currentUser}
      onLogout={handleLogout}
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      rosters={rosters}
      selectedRosterId={selectedRosterId}
      onSelectRosterId={setSelectedRosterId}
      conflictCount={conflictCount}
      onOpenGenerateModal={() => setShowGenerateModal(true)}
      searchQuery={searchQuery}
      onSearchChange={setSearchQuery}
      notifications={notifications}
      unreadCount={unreadCount}
      isConnected={isConnected}
      onMarkNotificationAsRead={markAsRead}
      onDeleteNotification={deleteNotification}
      onNavigateToRequest={() => setActiveTab('requests')}
    >
      {/* Dynamic View Router */}
      {activeTab === 'dashboard' && (
        <DashboardScreen
          rosters={rosters}
          selectedRosterId={selectedRosterId}
          onNavigate={setActiveTab}
          onOpenGenerateModal={() => setShowGenerateModal(true)}
        />
      )}

      {activeTab === 'analytics' && (
        <AnalyticsScreen
          rosters={rosters}
          selectedRosterId={selectedRosterId}
          onNavigateTab={setActiveTab}
          currentUser={currentUser}
        />
      )}

      {activeTab === 'requests' && (currentUser?.role === 'ADMIN' || currentUser?.role === 'OPERATIONS_MANAGER') && (
        <RequestsCenterScreen
          rosters={rosters}
          selectedRosterId={selectedRosterId}
          onRefreshRosters={loadRosters}
          onNavigateToConflicts={() => setActiveTab('conflicts')}
          onSelectRosterId={(id) => setSelectedRosterId(id)}
          currentUser={currentUser}
        />
      )}

      {activeTab === 'roster' && (
        <RosterCalendarScreen
          rosters={rosters}
          selectedRosterId={selectedRosterId}
          onRefreshRosters={loadRosters}
          onOpenGenerateModal={() => setShowGenerateModal(true)}
          searchQuery={searchQuery}
          onNavigateToConflicts={() => setActiveTab('conflicts')}
          currentUser={currentUser}
        />
      )}

      {activeTab === 'my-schedule' && (
        <EmployeePortalScreen />
      )}

      {activeTab === 'conflicts' && (
        <ConflictsScreen
          rosters={rosters}
          selectedRosterId={selectedRosterId}
          onRefreshRosters={loadRosters}
          currentUser={currentUser}
        />
      )}

      {activeTab === 'allocation-log' && (
        <AllocationLogScreen
          rosters={rosters}
          selectedRosterId={selectedRosterId}
        />
      )}

      {activeTab === 'employees' && (
        <WorkforceScreen initialSubTab="employees" searchQuery={searchQuery} currentUser={currentUser} />
      )}

      {activeTab === 'pods' && (
        <WorkforceScreen initialSubTab="pods" searchQuery={searchQuery} currentUser={currentUser} />
      )}

      {activeTab === 'brands' && <OperationsScreen initialSubTab="brands" />}

      {activeTab === 'assignments' && <OperationsScreen initialSubTab="assignments" />}

      {activeTab === 'history' && (
        <AuditHistoryScreen
          rosters={rosters}
          onSelectRosterId={(id) => {
            setSelectedRosterId(id);
            setActiveTab('roster');
          }}
          onCreateChildVersion={async (id) => {
            const child = await api.createChildVersion(id);
            await loadRosters();
            setSelectedRosterId(child.id);
            setActiveTab('roster');
          }}
          onPublishRoster={async (id) => {
            await api.publishRoster(id);
            await loadRosters();
          }}
        />
      )}

      {/* Global Generate Roster Modal */}
      <GenerateRosterModal
        isOpen={showGenerateModal}
        onClose={() => setShowGenerateModal(false)}
        onGenerated={async (newRoster) => {
          await loadRosters();
          setSelectedRosterId(newRoster.id);
          setActiveTab('roster');
        }}
      />
    </AppShell>
  );
};

export default App;
