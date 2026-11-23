import React, { useState, useEffect } from 'react';
import {
  Radio, Clock, CheckCircle2, X
} from 'lucide-react';

export default function ResponderTerminalModal({ isOpen, onClose, units = [], events = [] }) {
  const [selectedUnitId, setSelectedUnitId] = useState(units[0]?.id || 'NDRF-ALPHA-1');

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const currentUnit = units.find(u => u.id === selectedUnitId) || units[0];

  // Find all incidents assigned to this unit
  const assignedIncidents = events.filter(
    e => e.assigned_unit && e.assigned_unit.id === currentUnit?.id
  );

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="responder-terminal-title"
      className="fixed inset-0 z-[4000] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
    >
      <div className="bg-[#0c121e] border border-[#25354e] w-full max-w-3xl rounded shadow-2xl overflow-hidden flex flex-col max-h-[85vh] text-slate-100">
        {/* Terminal Header */}
        <div className="bg-[#090d16] p-3.5 border-b border-[#1f2b3e] flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded bg-[#131c2c] border border-[#263752] flex items-center justify-center text-emerald-400">
              <Radio className="w-3.5 h-3.5" />
            </div>
            <div>
              <h2 id="responder-terminal-title" className="text-xs font-bold text-slate-100 flex items-center space-x-2 font-mono">
                <span>TACTICAL FIELD RESPONDER TERMINAL (MDT)</span>
                <span className="text-[10px] bg-[#162520] text-emerald-300 border border-emerald-800 px-1.5 py-0.2 rounded">
                  VHF 142.550 MHz
                </span>
              </h2>
              <p className="text-[11px] text-slate-400">
                Encrypted low-bandwidth mobile & SMS dispatch receiver for on-ground rescue personnel
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-[#162030] transition"
            aria-label="Close Responder Terminal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content: Squad Select + Tactical Radio Feed */}
        <div className="p-4 overflow-y-auto flex-1 flex flex-col md:flex-row gap-3 text-xs">
          {/* Left Column: Fleet List */}
          <div className="w-full md:w-64 space-y-1.5 shrink-0">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block font-mono mb-1">
              Active First Responder Squads ({units.length})
            </span>
            {units.map((u) => {
              const isSelected = u.id === selectedUnitId;
              const unitAssigned = events.filter(e => e.assigned_unit?.id === u.id).length;

              return (
                <div
                  key={u.id}
                  onClick={() => setSelectedUnitId(u.id)}
                  className={`p-2.5 rounded border transition cursor-pointer ${
                    isSelected
                      ? 'bg-[#182436] border-blue-500/80 shadow-sm'
                      : 'bg-[#101726] border-[#1e2a3c] hover:border-[#2b3a54]'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-200 text-xs truncate">{u.name}</span>
                    <span className={`text-[9px] font-bold font-mono px-1.5 py-0.2 rounded ${
                      u.status === 'AVAILABLE' ? 'bg-[#032e22] text-emerald-300 border border-emerald-800' : 'bg-[#291e0a] text-amber-300 border border-amber-800'
                    }`}>
                      {u.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <span>{u.unit_type}</span>
                    <span className="text-sky-400">{unitAssigned} active mission(s)</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right Column: Tactical Radio/SMS Terminal for Selected Squad */}
          <div className="flex-1 bg-[#101726] border border-[#1e2a3c] rounded p-3.5 flex flex-col justify-between">
            {currentUnit ? (
              <div className="space-y-3">
                {/* Unit Details Header */}
                <div className="border-b border-[#1e2a3c] pb-2.5 flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-xs text-slate-100">{currentUnit.name}</h3>
                    <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5 font-mono">
                      <span>ID: <strong className="text-slate-300">{currentUnit.id}</strong></span>
                      <span>•</span>
                      <span>Contact: <strong className="text-slate-300">{currentUnit.contact}</strong></span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 block font-mono">BASE LOCATION</span>
                    <span className="text-[11px] font-mono text-cyan-400">
                      {currentUnit.lat.toFixed(4)}, {currentUnit.lng.toFixed(4)}
                    </span>
                  </div>
                </div>

                {/* Incoming Tactical SMS Dispatch Log */}
                <div>
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-2 font-mono">
                    Incoming SMS / Tactical Dispatch Log ({assignedIncidents.length})
                  </span>

                  {assignedIncidents.length === 0 ? (
                    <div className="bg-[#090d16] p-6 rounded border border-[#1a2538] text-center text-slate-400 text-xs">
                      <CheckCircle2 className="w-5 h-5 mx-auto mb-1 text-slate-400" />
                      Unit is on standby in patrol grid. No active crisis missions assigned.
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-56 overflow-y-auto pr-1 select-text">
                      {assignedIncidents.map((inc) => (
                        <div
                          key={inc.id}
                          className="bg-[#090d16] border border-[#1b273a] p-2.5 rounded space-y-1.5 font-mono text-[11px]"
                        >
                          <div className="flex items-center justify-between text-emerald-400 font-bold">
                            <span className="flex items-center">
                              <Radio className="w-3 h-3 mr-1 text-emerald-400" />
                              DISPATCH ALERT #{inc.id}
                            </span>
                            <span className="text-rose-400 text-xs">SEV {inc.severity}/10</span>
                          </div>

                          <div className="text-slate-300 font-sans text-xs">
                            <strong className="text-slate-200">LOCUS:</strong> {inc.sector} (GPS: {inc.coordinates.lat.toFixed(4)}, {inc.coordinates.lng.toFixed(4)})
                          </div>

                          <p className="text-slate-300 font-sans text-[11px] bg-[#0c121e] p-2 rounded border border-[#1a2538] leading-relaxed">
                            "{inc.summary}"
                          </p>

                          <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                            <span>Casualties: <strong className="text-slate-200">{inc.casualty_count}</strong></span>
                            <span className="text-sky-400 flex items-center font-mono">
                              <Clock className="w-3 h-3 mr-1" />
                              ETA: ~{inc.assigned_unit?.eta_minutes || 4} mins
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-slate-400 text-center py-10">Select a responder squad.</div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="bg-[#090d16] p-2.5 border-t border-[#1f2b3e] flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <span>ENCRYPTED FIRST RESPONDER TELEMETRY • CAD SYNC ACTIVE</span>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded bg-[#162030] hover:bg-[#1f2d44] text-slate-200 font-semibold transition"
          >
            Close Terminal
          </button>
        </div>
      </div>
    </div>
  );
}
