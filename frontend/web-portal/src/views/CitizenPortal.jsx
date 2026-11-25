import React, { useState } from 'react';
import { apiClient } from '../api/client';
import StatusBadge from '../components/StatusBadge';

export default function CitizenPortal() {
  const [activeTab, setActiveTab] = useState('report'); // 'report' | 'track'
  
  // Report Form State
  const [category, setCategory] = useState('POTHOLE');
  const [address, setAddress] = useState('');
  const [latitude, setLatitude] = useState(12.9716);
  const [longitude, setLongitude] = useState(77.5946);
  const [description, setDescription] = useState('');
  const [contact, setContact] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [createdTicket, setCreatedTicket] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Tracking State
  const [searchTicketId, setSearchTicketId] = useState('');
  const [trackedReport, setTrackedReport] = useState(null);
  const [trackError, setTrackError] = useState(null);
  const [searching, setSearching] = useState(false);

  // Auto-detect Geolocation
  const handleGetLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLatitude(parseFloat(pos.coords.latitude.toFixed(4)));
          setLongitude(parseFloat(pos.coords.longitude.toFixed(4)));
        },
        () => {
          alert('Location access denied or unavailable. Using default coordinates.');
        }
      );
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);
    setCreatedTicket(null);

    // Generate unique idempotency key
    const idempotencyKey = `CITIZEN-${Date.now()}-${Math.random().toString(36).substring(7)}`;

    try {
      const res = await apiClient.submitCitizenReport(
        {
          category,
          latitude: parseFloat(latitude),
          longitude: parseFloat(longitude),
          address,
          description,
          reporter_contact: contact || null,
        },
        idempotencyKey
      );
      setCreatedTicket(res);
      // Reset form
      setDescription('');
      setAddress('');
    } catch (err) {
      setErrorMsg(err.message || 'Submission failed. Please retry.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleTrack = async (e) => {
    e.preventDefault();
    if (!searchTicketId.trim()) return;
    setSearching(true);
    setTrackError(null);
    setTrackedReport(null);

    try {
      const res = await apiClient.getCitizenReportByTicket(searchTicketId.trim());
      if (!res) {
        setTrackError('Ticket not found. Verify ticket ID (e.g. HAZ-2026-XXXXX).');
      } else {
        setTrackedReport(res);
      }
    } catch (err) {
      setTrackError('Failed to query ticket status.');
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-emerald-950/70 via-slate-900 to-slate-950 p-6 rounded-2xl border border-emerald-800/40 shadow-xl">
        <div className="flex items-center space-x-3">
          <span className="text-3xl">📢</span>
          <div>
            <h1 className="text-xl font-bold text-white">
              Citizen Urban Infrastructure & Hazard Portal
            </h1>
            <p className="text-xs text-slate-300">
              Report road potholes, broken barriers, waterlogging, and garbage. Track municipal resolution in real-time.
            </p>
          </div>
        </div>

        {/* Sub-Tabs */}
        <div className="flex space-x-3 mt-6">
          <button
            onClick={() => setActiveTab('report')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
              activeTab === 'report'
                ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30'
                : 'bg-slate-800/80 text-slate-400 hover:text-white'
            }`}
          >
            ➕ File Hazard Report
          </button>
          <button
            onClick={() => setActiveTab('track')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
              activeTab === 'track'
                ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30'
                : 'bg-slate-800/80 text-slate-400 hover:text-white'
            }`}
          >
            🔎 Track Resolution Status
          </button>
        </div>
      </div>

      {/* Tab 1: File Hazard Report */}
      {activeTab === 'report' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          {createdTicket && (
            <div className="p-4 rounded-xl bg-emerald-950/80 border border-emerald-500/60 text-emerald-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold flex items-center gap-2">
                  ✅ Hazard Report Submitted Successfully!
                </span>
                <span className="font-mono text-sm px-2 py-0.5 rounded bg-emerald-900 text-emerald-100 border border-emerald-600">
                  {createdTicket.ticket_id}
                </span>
              </div>
              <p className="text-xs text-emerald-300">
                Save your ticket ID <strong>{createdTicket.ticket_id}</strong> to track municipal inspection, dispatch, and repair status.
              </p>
            </div>
          )}

          {errorMsg && (
            <div className="p-4 rounded-xl bg-rose-950/80 border border-rose-500/60 text-rose-200 text-sm">
              ❌ {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                  Hazard Category *
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  <option value="POTHOLE">🕳️ Pothole / Road Crater</option>
                  <option value="GARBAGE_DUMP">🗑️ Illegal Waste / Garbage Dump</option>
                  <option value="BROKEN_BARRIER">🚧 Broken Guardrail / Road Barrier</option>
                  <option value="WATERLOGGING">🌊 Severe Waterlogging / Drainage</option>
                  <option value="SIGNAL_FAILURE">🚦 Traffic Signal / Streetlight Failure</option>
                  <option value="ROAD_CRACK">⚡ Major Road Structural Crack</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                  Reporter Contact (Phone / Email - Optional)
                </label>
                <input
                  type="text"
                  placeholder="+91 98765 43210 or email"
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                Landmark / Street Address *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Near Metro Pillar 142, Outer Ring Road"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                  Latitude
                </label>
                <input
                  type="number"
                  step="any"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 text-sm font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                  Longitude
                </label>
                <input
                  type="number"
                  step="any"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 text-sm font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <button
                type="button"
                onClick={handleGetLocation}
                className="h-[42px] px-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium border border-slate-700 flex items-center justify-center gap-1.5 transition-colors"
              >
                📍 Detect Current GPS
              </button>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                Detailed Hazard Description *
              </label>
              <textarea
                required
                rows={3}
                placeholder="Describe size, depth, blockage, or safety hazard to traffic..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-semibold rounded-xl shadow-lg shadow-emerald-600/25 transition-all text-sm flex items-center justify-center gap-2"
            >
              {submitting ? 'Submitting to HA Ingestion...' : '🚀 Submit Official Civic Report'}
            </button>
          </form>
        </div>
      )}

      {/* Tab 2: Track Resolution Status */}
      {activeTab === 'track' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <form onSubmit={handleTrack} className="flex gap-3">
            <input
              type="text"
              required
              placeholder="Enter Ticket ID (e.g., HAZ-2026-A1B2C3)"
              value={searchTicketId}
              onChange={(e) => setSearchTicketId(e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
            />
            <button
              type="submit"
              disabled={searching}
              className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl text-sm transition-all"
            >
              {searching ? 'Checking...' : 'Check Status'}
            </button>
          </form>

          {trackError && (
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-slate-400 text-sm">
              ℹ️ {trackError}
            </div>
          )}

          {trackedReport && (
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <span className="text-xs text-slate-400 uppercase font-mono">
                    Ticket Reference
                  </span>
                  <h3 className="text-lg font-bold text-white font-mono">
                    {trackedReport.ticket_id}
                  </h3>
                </div>
                <StatusBadge status={trackedReport.status} />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                <div>
                  <span className="text-slate-500 block">Category</span>
                  <strong className="text-slate-200">{trackedReport.category}</strong>
                </div>
                <div>
                  <span className="text-slate-500 block">Priority</span>
                  <strong className="text-amber-400">{trackedReport.priority}</strong>
                </div>
                <div>
                  <span className="text-slate-500 block">Assigned Dept</span>
                  <strong className="text-slate-200">{trackedReport.assigned_department || 'Pending Triage'}</strong>
                </div>
                <div>
                  <span className="text-slate-500 block">Reported On</span>
                  <strong className="text-slate-200">{new Date(trackedReport.created_at).toLocaleDateString()}</strong>
                </div>
              </div>

              <div className="border-t border-slate-800/60 pt-3 text-xs space-y-2">
                <div>
                  <span className="text-slate-500 block">Location Address</span>
                  <span className="text-slate-300">{trackedReport.address} (Zone: {trackedReport.zone_id})</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Citizen Description</span>
                  <p className="text-slate-300 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                    {trackedReport.description}
                  </p>
                </div>
                {trackedReport.notes && (
                  <div>
                    <span className="text-emerald-400 block font-semibold">Municipal Investigation Notes</span>
                    <p className="text-emerald-200 bg-emerald-950/40 p-3 rounded-lg border border-emerald-800/40">
                      {trackedReport.notes}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
