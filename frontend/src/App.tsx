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
import { GenerateRosterModal } from './components/roster/GenerateRosterModal';
import { Activity } from 'lucide-react';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [loading, setLoading] = useState(true);
  const [rosters, setRosters] = useState<RosterSummary[]>([]);
  const [selectedRosterId, setSelectedRosterId] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showGenerateModal, setShowGenerateModal] = useState(false);

  useEffect(() => {
    checkAuth();
  }, []);

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
    } catch (err) {
      console.error('Failed to load rosters:', err);
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
      setCurrentUser(null);
    } catch (err) {
      console.error(err);
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
        />
      )}

      {activeTab === 'roster' && (
        <RosterCalendarScreen
          rosters={rosters}
          selectedRosterId={selectedRosterId}
          onRefreshRosters={loadRosters}
          onOpenGenerateModal={() => setShowGenerateModal(true)}
          searchQuery={searchQuery}
        />
      )}

      {activeTab === 'conflicts' && (
        <ConflictsScreen
          rosters={rosters}
          selectedRosterId={selectedRosterId}
          onRefreshRosters={loadRosters}
        />
      )}

      {activeTab === 'allocation-log' && (
        <AllocationLogScreen
          rosters={rosters}
          selectedRosterId={selectedRosterId}
        />
      )}

      {activeTab === 'employees' && (
        <WorkforceScreen initialSubTab="employees" searchQuery={searchQuery} />
      )}

      {activeTab === 'pods' && (
        <WorkforceScreen initialSubTab="pods" searchQuery={searchQuery} />
      )}

      {activeTab === 'leaves' && (
        <WorkforceScreen initialSubTab="leaves" searchQuery={searchQuery} />
      )}

      {activeTab === 'brands' && <OperationsScreen initialSubTab="brands" />}

      {activeTab === 'assignments' && <OperationsScreen initialSubTab="assignments" />}

      {activeTab === 'rules' && <OperationsScreen initialSubTab="rules" />}

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
