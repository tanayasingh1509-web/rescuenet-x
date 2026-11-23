import React from 'react';
import {
  Radio, Phone, Smartphone, Presentation, Key,
  ShieldAlert, Activity, Truck, CheckCircle2
} from 'lucide-react';

export default function HeaderStats({
  events = [],
  units = [],
  wsConnected = false,
  latencyMs = 0,
  onOpenCitizenPortal,
  onOpenPhoneSimulator,
  onOpenPitchDeck,
  onOpenResponderTerminal,
  onOpenApiKeys
}) {
  const totalCount = events.length;
  const criticalCount = events.filter((e) => e.severity >= 8).length;
  const activeDispatched = events.filter((e) => e.status === 'DISPATCHED').length;
  const availableUnits = units.filter((u) => u.status === 'AVAILABLE').length;
  const verifiedCount = events.filter((e) => e.verified).length;
  const verifiedPct = totalCount > 0 ? Math.round((verifiedCount / totalCount) * 100) : null;

  return (
    <header className="bg-[#0b101a] border-b border-[#1b2537] px-4 lg:px-6 py-2.5 sticky top-0 z-50 text-slate-100 font-sans">
      {/* Top Bar: Brand, Channels, and Dispatch Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Brand & CAD Identity */}
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded bg-[#162032] border border-[#2c3d59] flex items-center justify-center text-rose-500 shrink-0">
            <Radio className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2.5">
              <h1 className="text-base font-extrabold tracking-wider text-slate-100 font-mono">
                RESCUENET-X
              </h1>
              <span className="text-[10px] uppercase font-bold tracking-widest bg-[#1c283d] text-slate-300 border border-[#2b3d5b] px-2 py-0.5 rounded font-mono">
                CIVIL DEFENSE CAD
              </span>
              <span className="hidden sm:inline-block text-[10px] text-slate-400 font-mono">
                GATEWAY: SEC-18
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Omnichannel Crisis Intelligence & Automated Unit CAD Dispatch
            </p>
          </div>
        </div>

        {/* Action Controls & Telemetry */}
        <div className="flex items-center space-x-2 text-xs flex-wrap gap-y-2">
          {/* API Keys Configuration */}
          <button
            onClick={onOpenApiKeys}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded bg-[#131b29] hover:bg-[#1a2538] border border-[#24334a] text-slate-200 hover:text-white transition font-medium focus-visible:ring-2 focus-visible:ring-blue-500"
            title="Configure Google Gemini, Mapbox, and Twilio API Keys"
            aria-label="Open API Keys modal"
          >
            <Key className="w-3.5 h-3.5 text-blue-400" />
            <span>API Keys</span>
          </button>

          {/* Tactical Responder Radios */}
          <button
            onClick={onOpenResponderTerminal}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded bg-[#131b29] hover:bg-[#1a2538] border border-[#24334a] text-slate-200 hover:text-white transition font-medium focus-visible:ring-2 focus-visible:ring-blue-500"
            title="Field Responder Mobile Data Terminal & VHF Radios"
            aria-label="Open Field Terminal modal"
          >
            <Radio className="w-3.5 h-3.5 text-emerald-400" />
            <span>Field Terminal</span>
          </button>

          {/* 2G Telephony Simulator */}
          <button
            onClick={onOpenPhoneSimulator}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded bg-[#131b29] hover:bg-[#1a2538] border border-[#24334a] text-slate-200 hover:text-white transition font-medium focus-visible:ring-2 focus-visible:ring-blue-500"
            title="2G Feature Phone IVR & DTMF Keypad Simulator"
            aria-label="Open 2G Phone Simulator"
          >
            <Phone className="w-3.5 h-3.5 text-cyan-400" />
            <span>2G Simulator</span>
          </button>

          {/* Citizen SOS Portal */}
          <button
            onClick={onOpenCitizenPortal}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded bg-rose-950/70 hover:bg-rose-900 border border-rose-800 text-rose-200 hover:text-white transition font-medium focus-visible:ring-2 focus-visible:ring-rose-500"
            title="Citizen Distress Portal (Mobile PWA Mesh)"
            aria-label="Open Citizen SOS Portal"
          >
            <Smartphone className="w-3.5 h-3.5 text-rose-400" />
            <span>Citizen SOS</span>
          </button>

          {/* Pitch Deck / Architecture Docs */}
          <button
            onClick={onOpenPitchDeck}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded bg-[#131b29] hover:bg-[#1a2538] border border-[#24334a] text-slate-300 hover:text-white transition font-medium focus-visible:ring-2 focus-visible:ring-blue-500"
            title="System Architecture & Judge Briefing Deck"
            aria-label="Open Briefing Pitch Deck"
          >
            <Presentation className="w-3.5 h-3.5 text-slate-400" />
            <span>Briefing</span>
          </button>

          {/* Connection & Latency Telemetry */}
          <div
            className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded border font-mono text-[11px] ${
              wsConnected
                ? 'bg-[#0f231d] border-emerald-800 text-emerald-300'
                : 'bg-[#291316] border-rose-900 text-rose-300'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-rose-500'}`} />
            <span>{wsConnected ? `STREAM LIVE (${latencyMs}ms)` : 'OFFLINE'}</span>
          </div>
        </div>
      </div>

      {/* KPI Stats Ribbon: Measured or explicit DEMO stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-2.5 pt-2.5 border-t border-[#1b2537] text-xs">
        {/* Active Queue */}
        <div className="bg-[#0f1624] border border-[#1c283c] rounded px-3 py-2 flex items-center justify-between">
          <div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Active Incidents</div>
            <div className="text-base font-bold text-slate-100 font-mono tabular-nums">{totalCount}</div>
          </div>
          <Activity className="w-4 h-4 text-slate-400" />
        </div>

        {/* Critical Alerts */}
        <div
          className={`border rounded px-3 py-2 flex items-center justify-between transition ${
            criticalCount > 0 ? 'bg-[#211116] border-rose-800/80' : 'bg-[#0f1624] border-[#1c283c]'
          }`}
        >
          <div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Critical Priority (8-10)</div>
            <div className="text-base font-bold text-rose-400 font-mono tabular-nums">{criticalCount}</div>
          </div>
          <ShieldAlert className={`w-4 h-4 ${criticalCount > 0 ? 'text-rose-400' : 'text-slate-400'}`} />
        </div>

        {/* Fleet Deployment */}
        <div className="bg-[#0f1624] border border-[#1c283c] rounded px-3 py-2 flex items-center justify-between">
          <div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Fleet Status</div>
            <div className="text-base font-bold text-amber-400 font-mono tabular-nums">
              {activeDispatched} <span className="text-xs font-normal text-slate-400">en route ({availableUnits} avail)</span>
            </div>
          </div>
          <Truck className="w-4 h-4 text-slate-400" />
        </div>

        {/* Triage & Verification Metric */}
        <div className="bg-[#0f1624] border border-[#1c283c] rounded px-3 py-2 flex items-center justify-between">
          <div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Verified Rate</div>
            <div className="text-base font-bold text-emerald-400 font-mono tabular-nums">
              {verifiedPct !== null ? (
                <>
                  {verifiedPct}% <span className="text-[10px] font-normal text-slate-400 font-mono">({verifiedCount}/{totalCount})</span>
                </>
              ) : (
                <span className="text-xs text-slate-400 font-mono">DEMO READY</span>
              )}
            </div>
          </div>
          <CheckCircle2 className="w-4 h-4 text-slate-400" />
        </div>
      </div>
    </header>
  );
}
