import React from 'react';
import StatusBadge from './StatusBadge';

export default function HotspotMap({ hotspots = [] }) {
  return (
    <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <span>📍</span> Urban Incident Hotspots & High-Risk Zones
          </h3>
          <p className="text-xs text-slate-400">
            Automated cluster aggregation of ALPR violations and citizen hazard reports
          </p>
        </div>
        <span className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-slate-300">
          {hotspots.length} Monitored Zones
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {hotspots.map((zone) => {
          const isHigh = zone.risk_level === 'SEVERE' || zone.risk_level === 'HIGH';
          return (
            <div
              key={zone.zone_id}
              className={`p-4 rounded-lg border transition-all ${
                isHigh
                  ? 'border-rose-900/40 bg-rose-950/20 hover:border-rose-700/60'
                  : 'border-slate-800 bg-slate-950/40 hover:border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-semibold text-sm text-slate-200">
                    {zone.zone_name}
                  </h4>
                  <p className="text-xs font-mono text-slate-400">
                    {zone.zone_id} • Radius: {zone.radius_meters}m
                  </p>
                </div>
                <StatusBadge status={zone.risk_level} />
              </div>

              <div className="mt-3 flex items-center justify-between text-xs text-slate-300 border-t border-slate-800/60 pt-2 font-mono">
                <span>Violations: <strong className="text-amber-400">{zone.violation_count}</strong></span>
                <span>Hazards: <strong className="text-cyan-400">{zone.hazard_count}</strong></span>
                <span className="text-slate-400">Lat: {zone.latitude.toFixed(3)}, Lon: {zone.longitude.toFixed(3)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
