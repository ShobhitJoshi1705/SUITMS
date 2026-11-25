import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import AuthorityDashboard from './views/AuthorityDashboard';
import CitizenPortal from './views/CitizenPortal';
import ChallanSearch from './views/ChallanSearch';
import { apiClient } from './api/client';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' | 'citizen' | 'challans'
  const [systemStatus, setSystemStatus] = useState(null);
  const [realTimeEvents, setRealTimeEvents] = useState([]);

  // Check HA Cluster Health
  const checkHealth = async () => {
    try {
      const health = await apiClient.getHealth();
      setSystemStatus(health);
    } catch (e) {
      setSystemStatus({ ready: false });
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === 'dashboard' && (
          <AuthorityDashboard realTimeEvents={realTimeEvents} />
        )}
        {activeTab === 'citizen' && (
          <CitizenPortal />
        )}
        {activeTab === 'challans' && (
          <ChallanSearch />
        )}
      </main>

      <footer className="border-t border-slate-900 py-4 px-6 text-center text-xs text-slate-500 font-mono">
        SUITMS • Smart Urban Infrastructure & Traffic Management System • HA Multi-Node Cluster
      </footer>
    </div>
  );
}
