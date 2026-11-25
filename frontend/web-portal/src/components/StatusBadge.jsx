import React from 'react';

export default function StatusBadge({ status, type = 'default' }) {
  let color = 'bg-slate-800 text-slate-300 border-slate-700';

  const normalized = (status || '').toUpperCase();

  // Challan statuses
  if (normalized === 'PAID' || normalized === 'RESOLVED') {
    color = 'bg-emerald-950/60 text-emerald-300 border-emerald-700/50';
  } else if (normalized === 'ISSUED' || normalized === 'PENDING' || normalized === 'REPORTED') {
    color = 'bg-amber-950/60 text-amber-300 border-amber-700/50';
  } else if (normalized === 'DISMISSED' || normalized === 'REJECTED') {
    color = 'bg-slate-800 text-slate-400 border-slate-700';
  } else if (normalized === 'IN_REVIEW') {
    color = 'bg-sky-950/60 text-sky-300 border-sky-700/50';
  } else if (normalized === 'DISPATCHED') {
    color = 'bg-indigo-950/60 text-indigo-300 border-indigo-700/50';
  } else if (normalized === 'CRITICAL' || normalized === 'SEVERE') {
    color = 'bg-rose-950/60 text-rose-300 border-rose-700/50 animate-pulse';
  } else if (normalized === 'HIGH') {
    color = 'bg-orange-950/60 text-orange-300 border-orange-700/50';
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border font-mono ${color}`}>
      {status}
    </span>
  );
}
