import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';
import HotspotMap from '../components/HotspotMap';

export default function AuthorityDashboard({ realTimeEvents = [] }) {
  const [subTab, setSubTab] = useState('violations'); // 'violations' | 'challans' | 'reports' | 'hotspots'
  const [summary, setSummary] = useState(null);
  const [violations, setViolations] = useState([]);
  const [challans, setChallans] = useState([]);
  const [reports, setReports] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState(false);

  // Filters
  const [plateFilter, setPlateFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [sumRes, vioRes, chRes, repRes, hotRes] = await Promise.all([
        apiClient.getSummary().catch(() => null),
        apiClient.getViolations({ limit: 30 }).catch(() => []),
        apiClient.getChallans({ limit: 30 }).catch(() => []),
        apiClient.getCitizenReports({ limit: 30 }).catch(() => []),
        apiClient.getHotspots().catch(() => []),
      ]);

      if (sumRes) setSummary(sumRes);
      setViolations(vioRes || []);
      setChallans(chRes || []);
      setReports(repRes || []);
      setHotspots(hotRes || []);
    } catch (e) {
      console.error('Data reload error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 8000); // Poll every 8s
    return () => clearInterval(interval);
  }, []);

  const handleSimulateEdgeEvent = async () => {
    setSimulating(true);
    try {
      await apiClient.triggerEdgeSimulationEvent();
      setTimeout(loadData, 500);
    } catch (e) {
      alert('Simulation error: ' + e.message);
    } finally {
      setSimulating(false);
    }
  };

  const handleUpdateReportStatus = async (ticketId, nextStatus) => {
    try {
      await apiClient.updateCitizenReport(ticketId, {
        status: nextStatus,
        notes: `Status advanced to ${nextStatus} by Traffic Control Authority.`
      });
      loadData();
    } catch (e) {
      alert('Failed to update report status: ' + e.message);
    }
  };

  const filteredViolations = violations.filter((v) => {
    return !plateFilter || (v.plate_number && v.plate_number.toLowerCase().includes(plateFilter.toLowerCase()));
  });

  const filteredChallans = challans.filter((c) => {
    const matchesPlate = !plateFilter || (c.plate_number && c.plate_number.toLowerCase().includes(plateFilter.toLowerCase()));
    const matchesStatus = !statusFilter || c.status === statusFilter;
    return matchesPlate && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/60 p-4 rounded-2xl border border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span>🚦</span> Urban Traffic & Infrastructure Intelligence Command
          </h2>
          <p className="text-xs text-slate-400">
            Automated ALPR, YOLOv8 Violation Pipeline & Municipal Hazard Resolution Hub
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleSimulateEdgeEvent}
            disabled={simulating}
            className="px-3.5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-blue-600/30 flex items-center gap-1.5 transition-all"
          >
            <span>⚡</span> {simulating ? 'Ingesting Event...' : 'Trigger Edge Camera Event'}
          </button>
          <button
            onClick={loadData}
            disabled={loading}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium border border-slate-700 transition-colors"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* KPI Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="Violations Detected Today"
          value={summary?.total_violations_today ?? violations.length}
          subtitle="Real-time camera pipeline"
          icon="🚨"
          color="rose"
        />
        <MetricCard
          title="Active Challans Pending"
          value={summary?.active_challans_count ?? challans.filter(c => c.status === 'ISSUED').length}
          subtitle="Unpaid automated tickets"
          icon="🎫"
          color="amber"
        />
        <MetricCard
          title="Fines Collected (INR)"
          value={`₹${(summary?.total_fines_collected ?? 0).toLocaleString()}`}
          subtitle="Electronic payments reconciled"
          icon="💰"
          color="emerald"
        />
        <MetricCard
          title="Open Citizen Hazards"
          value={summary?.open_hazards_count ?? reports.filter(r => r.status !== 'RESOLVED').length}
          subtitle="Potholes & safety defects"
          icon="🚧"
          color="blue"
        />
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setSubTab('violations')}
          className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${
            subTab === 'violations'
              ? 'bg-slate-800 text-blue-400 border border-slate-700'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          📷 Live Violations & ALPR ({violations.length})
        </button>
        <button
          onClick={() => setSubTab('challans')}
          className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${
            subTab === 'challans'
              ? 'bg-slate-800 text-amber-400 border border-slate-700'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          🎫 Automated Challans ({challans.length})
        </button>
        <button
          onClick={() => setSubTab('reports')}
          className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${
            subTab === 'reports'
              ? 'bg-slate-800 text-emerald-400 border border-slate-700'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          📢 Civic Hazard Triage ({reports.length})
        </button>
        <button
          onClick={() => setSubTab('hotspots')}
          className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${
            subTab === 'hotspots'
              ? 'bg-slate-800 text-purple-400 border border-slate-700'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          🗺️ Hotspots & Risk Analytics
        </button>
      </div>

      {/* Sub-Tab 1: Violations & ALPR Table */}
      {subTab === 'violations' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between gap-4">
            <input
              type="text"
              placeholder="Filter by License Plate..."
              value={plateFilter}
              onChange={(e) => setPlateFilter(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-200 placeholder:text-slate-500 uppercase"
            />
            <span className="text-xs text-slate-400 font-mono">
              Showing {filteredViolations.length} records
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono border-b border-slate-800">
                <tr>
                  <th className="p-3">Plate Number</th>
                  <th className="p-3">Violation Offense</th>
                  <th className="p-3">Camera Node</th>
                  <th className="p-3">Confidence</th>
                  <th className="p-3">Timestamp</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {filteredViolations.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="p-3 font-bold text-amber-300">
                      {v.plate_number || 'UNKNOWN'}
                    </td>
                    <td className="p-3 text-slate-200">
                      {v.violation_type}
                    </td>
                    <td className="p-3 text-slate-400">
                      {v.camera_id} ({v.zone_id})
                    </td>
                    <td className="p-3">
                      <span className="text-emerald-400">{(v.confidence * 100).toFixed(1)}%</span>
                    </td>
                    <td className="p-3 text-slate-400">
                      {new Date(v.created_at).toLocaleTimeString()}
                    </td>
                    <td className="p-3">
                      <StatusBadge status={v.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sub-Tab 2: Challans Management */}
      {subTab === 'challans' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between gap-4">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Search Plate Number..."
                value={plateFilter}
                onChange={(e) => setPlateFilter(e.target.value)}
                className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-200 uppercase"
              />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200"
              >
                <option value="">All Statuses</option>
                <option value="ISSUED">ISSUED</option>
                <option value="PAID">PAID</option>
                <option value="DISMISSED">DISMISSED</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono border-b border-slate-800">
                <tr>
                  <th className="p-3">Challan #</th>
                  <th className="p-3">Vehicle Plate</th>
                  <th className="p-3">Violation</th>
                  <th className="p-3">Fine Amount</th>
                  <th className="p-3">Issued Date</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {filteredChallans.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="p-3 font-semibold text-slate-200">
                      {c.challan_number}
                    </td>
                    <td className="p-3 font-bold text-amber-300">
                      {c.plate_number}
                    </td>
                    <td className="p-3 text-slate-300">
                      {c.violation_type}
                    </td>
                    <td className="p-3 text-white font-bold">
                      ₹{c.fine_amount.toFixed(2)}
                    </td>
                    <td className="p-3 text-slate-400">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-3">
                      <StatusBadge status={c.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sub-Tab 3: Citizen Hazard Reports Triage */}
      {subTab === 'reports' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono border-b border-slate-800">
                <tr>
                  <th className="p-3">Ticket ID</th>
                  <th className="p-3">Category</th>
                  <th className="p-3">Address</th>
                  <th className="p-3">Priority</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Action Triage</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {reports.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="p-3 font-mono font-bold text-cyan-300">
                      {r.ticket_id}
                    </td>
                    <td className="p-3 font-medium text-slate-200">
                      {r.category}
                    </td>
                    <td className="p-3 text-slate-400 max-w-xs truncate">
                      {r.address}
                    </td>
                    <td className="p-3">
                      <StatusBadge status={r.priority} />
                    </td>
                    <td className="p-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="p-3">
                      <div className="flex gap-1.5">
                        {r.status === 'REPORTED' && (
                          <button
                            onClick={() => handleUpdateReportStatus(r.ticket_id, 'IN_REVIEW')}
                            className="px-2 py-1 bg-sky-900/60 hover:bg-sky-800 text-sky-200 rounded text-[11px] font-mono border border-sky-700/50"
                          >
                            Review
                          </button>
                        )}
                        {r.status === 'IN_REVIEW' && (
                          <button
                            onClick={() => handleUpdateReportStatus(r.ticket_id, 'DISPATCHED')}
                            className="px-2 py-1 bg-indigo-900/60 hover:bg-indigo-800 text-indigo-200 rounded text-[11px] font-mono border border-indigo-700/50"
                          >
                            Dispatch Team
                          </button>
                        )}
                        {r.status === 'DISPATCHED' && (
                          <button
                            onClick={() => handleUpdateReportStatus(r.ticket_id, 'RESOLVED')}
                            className="px-2 py-1 bg-emerald-900/60 hover:bg-emerald-800 text-emerald-200 rounded text-[11px] font-mono border border-emerald-700/50"
                          >
                            Resolve
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sub-Tab 4: Hotspots */}
      {subTab === 'hotspots' && (
        <HotspotMap hotspots={hotspots} />
      )}
    </div>
  );
}
