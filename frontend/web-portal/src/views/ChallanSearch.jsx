import React, { useState } from 'react';
import { apiClient } from '../api/client';
import StatusBadge from '../components/StatusBadge';

export default function ChallanSearch() {
  const [identifier, setIdentifier] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [challan, setChallan] = useState(null);
  const [paymentSuccess, setPaymentSuccess] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!identifier.trim()) return;
    setLoading(true);
    setError(null);
    setChallan(null);
    setPaymentSuccess(false);

    try {
      const res = await apiClient.getChallanById(identifier.trim());
      if (!res) {
        setError(`No active challan found for "${identifier}". Verify vehicle plate number or challan ID.`);
      } else {
        setChallan(res);
      }
    } catch (err) {
      setError('Unable to query challan details. Please check network connectivity.');
    } finally {
      setLoading(false);
    }
  };

  const handlePay = async () => {
    if (!challan) return;
    setLoading(true);
    try {
      const updated = await apiClient.payChallan(challan.challan_number);
      setChallan(updated);
      setPaymentSuccess(true);
    } catch (err) {
      alert('Payment processing failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-amber-950/70 via-slate-900 to-slate-950 p-6 rounded-2xl border border-amber-800/40 shadow-xl">
        <div className="flex items-center space-x-3">
          <span className="text-3xl">💳</span>
          <div>
            <h1 className="text-xl font-bold text-white">
              Online Traffic Violation Challan Clearance
            </h1>
            <p className="text-xs text-slate-300">
              Query traffic enforcement tickets by vehicle registration number (e.g., KA01AB1234) or Challan ID.
            </p>
          </div>
        </div>
      </div>

      {/* Search Input Box */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <form onSubmit={handleSearch} className="flex gap-3">
          <input
            type="text"
            required
            placeholder="Enter Plate Number (e.g. KA01AB1234) or Challan # (CH-2026-...)"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value.toUpperCase())}
            className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-base font-mono text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-amber-500 uppercase"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-3 bg-amber-600 hover:bg-amber-500 disabled:bg-slate-800 text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-amber-600/30"
          >
            {loading ? 'Searching...' : 'Search Ticket'}
          </button>
        </form>

        {error && (
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-slate-400 text-sm">
            ℹ️ {error}
          </div>
        )}

        {paymentSuccess && (
          <div className="p-4 rounded-xl bg-emerald-950/80 border border-emerald-500/60 text-emerald-200 text-sm flex items-center justify-between">
            <span>🎉 Payment processed successfully! Electronic Challan status updated to <strong>PAID</strong>.</span>
          </div>
        )}

        {challan && (
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <span className="text-xs text-slate-400 uppercase font-mono">Challan Reference</span>
                <h3 className="text-xl font-extrabold text-white font-mono">
                  {challan.challan_number}
                </h3>
              </div>
              <StatusBadge status={challan.status} />
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs font-mono">
              <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                <span className="text-slate-500 block">Vehicle Registration</span>
                <strong className="text-base text-amber-300">{challan.plate_number}</strong>
              </div>
              <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                <span className="text-slate-500 block">Violation Offense</span>
                <strong className="text-base text-rose-300">{challan.violation_type}</strong>
              </div>
              <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                <span className="text-slate-500 block">Fine Penalty Amount</span>
                <strong className="text-base text-white">₹{challan.fine_amount.toFixed(2)}</strong>
              </div>
            </div>

            <div className="flex justify-between items-center text-xs text-slate-400 font-mono border-t border-slate-800/80 pt-3">
              <span>Issued On: {new Date(challan.created_at).toLocaleString()}</span>
              <span>Due By: {new Date(challan.due_date).toLocaleDateString()}</span>
            </div>

            {challan.status === 'ISSUED' && (
              <div className="pt-2">
                <button
                  onClick={handlePay}
                  disabled={loading}
                  className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold rounded-xl shadow-lg shadow-emerald-600/30 text-sm transition-all"
                >
                  💳 Pay Fine Online (₹{challan.fine_amount.toFixed(2)})
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
