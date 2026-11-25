import React from 'react';

export default function MetricCard({ title, value, subtitle, icon, trend, color = 'blue' }) {
  const colorMap = {
    blue: 'from-blue-600/20 to-cyan-600/10 border-blue-500/30 text-blue-400',
    amber: 'from-amber-600/20 to-orange-600/10 border-amber-500/30 text-amber-400',
    emerald: 'from-emerald-600/20 to-teal-600/10 border-emerald-500/30 text-emerald-400',
    rose: 'from-rose-600/20 to-pink-600/10 border-rose-500/30 text-rose-400',
    purple: 'from-purple-600/20 to-indigo-600/10 border-purple-500/30 text-purple-400',
  };

  return (
    <div className={`p-5 rounded-xl border bg-gradient-to-br ${colorMap[color]} backdrop-blur-md shadow-lg transition-transform hover:-translate-y-1`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        <span className="text-2xl">{icon}</span>
      </div>
      <div className="flex items-baseline space-x-2">
        <span className="text-3xl font-extrabold tracking-tight text-white font-mono">
          {value}
        </span>
        {trend && (
          <span className="text-xs font-medium text-emerald-400">
            {trend}
          </span>
        )}
      </div>
      {subtitle && (
        <p className="mt-1 text-xs text-slate-400">
          {subtitle}
        </p>
      )}
    </div>
  );
}
