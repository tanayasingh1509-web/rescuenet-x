import React, { useState } from 'react';
import {
  Flame, Waves, HeartPulse, ShieldAlert, LifeBuoy,
  Phone, Camera, Smartphone, CheckCircle2,
  Search, AlertCircle, Send
} from 'lucide-react';

export default function IncidentFeed({
  events = [],
  selectedEvent,
  onSelectEvent,
  onDispatch
}) {
  const [filterCategory, setFilterCategory] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [onlyCritical, setOnlyCritical] = useState(false);

  // Category Icon Resolver
  const getCategoryIcon = (category) => {
    switch (category) {
      case 'FIRE': return <Flame className="w-3.5 h-3.5 text-orange-400" />;
      case 'FLOOD': return <Waves className="w-3.5 h-3.5 text-cyan-400" />;
      case 'AMBULANCE': return <HeartPulse className="w-3.5 h-3.5 text-emerald-400" />;
      case 'POLICE': return <ShieldAlert className="w-3.5 h-3.5 text-blue-400" />;
      default: return <LifeBuoy className="w-3.5 h-3.5 text-rose-400" />;
    }
  };

  // Channel Source Badge Resolver
  const getSourceBadge = (source) => {
    switch (source) {
      case 'voice':
        return (
          <span className="inline-flex items-center space-x-1 text-[10px] text-cyan-400 font-mono bg-cyan-950/60 border border-cyan-800/80 px-1.5 py-0.5 rounded">
            <Phone className="w-2.5 h-2.5" />
            <span>2G GSM</span>
          </span>
        );
      case 'image':
        return (
          <span className="inline-flex items-center space-x-1 text-[10px] text-amber-400 font-mono bg-amber-950/60 border border-amber-800/80 px-1.5 py-0.5 rounded">
            <Camera className="w-2.5 h-2.5" />
            <span>YOLO AI</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 text-[10px] text-emerald-400 font-mono bg-emerald-950/60 border border-emerald-800/80 px-1.5 py-0.5 rounded">
            <Smartphone className="w-2.5 h-2.5" />
            <span>PWA MESH</span>
          </span>
        );
    }
  };

  const filteredEvents = events.filter((ev) => {
    if (filterCategory !== 'ALL' && ev.category !== filterCategory) return false;
    if (onlyCritical && ev.severity < 8) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchSector = ev.sector && ev.sector.toLowerCase().includes(q);
      const matchSummary = ev.summary && ev.summary.toLowerCase().includes(q);
      const matchCat = ev.category && ev.category.toLowerCase().includes(q);
      if (!matchSector && !matchSummary && !matchCat) return false;
    }
    return true;
  });

  return (
    <aside className="w-full lg:w-96 flex flex-col h-full bg-[#0d121c] border-r border-[#1c2738] text-slate-100 overflow-hidden">
      {/* Search & Filter Header */}
      <div className="p-3 border-b border-[#1c2738] bg-[#090d15] space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Incident Queue
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 bg-[#172030] text-slate-300 border border-[#273752] rounded">
              {filteredEvents.length}
            </span>
          </div>

          <label className="flex items-center space-x-1.5 text-[11px] text-rose-300 cursor-pointer">
            <input
              type="checkbox"
              checked={onlyCritical}
              onChange={(e) => setOnlyCritical(e.target.checked)}
              className="rounded border-[#2d3e58] bg-[#111724] text-rose-500 focus:ring-0 cursor-pointer"
            />
            <span className="font-medium">Priority 1 Only</span>
          </label>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Filter sector, summary, or ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-[#121826] border border-[#223045] rounded text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition select-text"
            aria-label="Filter incidents by sector, summary, or ID"
          />
        </div>

        {/* Segmented Category Filter Bar */}
        <div className="flex items-center space-x-1 overflow-x-auto pb-0.5 text-[10px] font-medium no-scrollbar">
          {['ALL', 'FLOOD', 'FIRE', 'AMBULANCE', 'RESCUE', 'POLICE'].map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-2 py-1 rounded transition whitespace-nowrap ${
                filterCategory === cat
                  ? 'bg-[#1e2a3e] text-white font-bold border border-[#334666]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#131b2a]'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Incident List */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
        {filteredEvents.length === 0 ? (
          <div className="text-center py-14 text-slate-500 text-xs space-y-1">
            <AlertCircle className="w-6 h-6 mx-auto text-slate-600 mb-1" />
            <div className="font-semibold text-slate-400">No matching incidents in queue</div>
            <p className="text-[11px]">Clear search or filter criteria to view all active reports.</p>
          </div>
        ) : (
          filteredEvents.map((ev) => {
            const isSelected = selectedEvent && selectedEvent.id === ev.id;
            const isCritical = ev.severity >= 8;
            const isDispatched = ev.status === 'DISPATCHED';

            const severityBorder = isCritical
              ? 'border-l-rose-500'
              : ev.severity >= 5
              ? 'border-l-amber-500'
              : 'border-l-blue-500';

            return (
              <div
                key={ev.id}
                onClick={() => onSelectEvent(ev)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectEvent(ev);
                  }
                }}
                tabIndex={0}
                role="button"
                aria-pressed={isSelected}
                className={`p-2.5 rounded border border-l-4 transition cursor-pointer text-left focus:outline-none focus:ring-1 focus:ring-blue-500 ${severityBorder} ${
                  isSelected
                    ? 'bg-[#182335] border-blue-500/80 shadow-sm'
                    : 'bg-[#101622] border-[#1d2738] hover:bg-[#141c2c] hover:border-[#26354c]'
                }`}
              >
                {/* Header Row: Category, Severity, Channel Source */}
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center space-x-1.5">
                    {getCategoryIcon(ev.category)}
                    <span className="font-bold text-xs uppercase tracking-wide text-slate-100">
                      {ev.category}
                    </span>
                    {getSourceBadge(ev.source)}
                  </div>

                  <div className="flex items-center space-x-1.5">
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded font-mono ${
                        isCritical
                          ? 'bg-rose-950/80 text-rose-300 border border-rose-800'
                          : ev.severity >= 5
                          ? 'bg-amber-950/80 text-amber-300 border border-amber-800'
                          : 'bg-blue-950/80 text-blue-300 border border-blue-800'
                      }`}
                    >
                      SEV {ev.severity}/10
                    </span>
                  </div>
                </div>

                {/* Sector / Location Name */}
                <div className="text-xs font-semibold text-slate-200 mb-1 flex items-center justify-between">
                  <span className="truncate">{ev.sector || 'Disaster Sector'}</span>
                  {ev.cluster_count > 1 && (
                    <span className="text-[10px] bg-[#1a2333] text-indigo-300 border border-indigo-900 px-1 rounded font-mono shrink-0 ml-1">
                      {ev.cluster_count} merged
                    </span>
                  )}
                </div>

                {/* Tactical Synopsis */}
                <p className="text-[11px] text-slate-400 line-clamp-2 mb-2 leading-relaxed">
                  {ev.summary || 'Emergency incident reported via multi-modal sensor stream.'}
                </p>

                {/* Footer Row: Casualties, Assignment, Dispatch Button */}
                <div className="flex items-center justify-between pt-1.5 border-t border-[#1b2537] text-[10px]">
                  <div className="flex items-center space-x-2 text-slate-400">
                    <span>Casualties: <strong className="text-slate-200 font-mono">{ev.casualty_count}</strong></span>
                    <span className="text-slate-600">•</span>
                    <span className={isDispatched ? 'text-emerald-400 font-semibold' : 'text-amber-400 font-semibold'}>
                      {isDispatched ? 'DISPATCHED' : 'UNASSIGNED'}
                    </span>
                  </div>

                  {!isDispatched ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDispatch(ev.id);
                      }}
                      className="flex items-center space-x-1 bg-rose-700 hover:bg-rose-600 text-white font-bold px-2 py-0.5 rounded transition focus:outline-none focus:ring-1 focus:ring-rose-400"
                      title="Authorize Immediate Automated Unit Dispatch"
                    >
                      <Send className="w-2.5 h-2.5" />
                      <span>Dispatch</span>
                    </button>
                  ) : (
                    <span className="text-[10px] text-emerald-400 font-mono flex items-center">
                      <CheckCircle2 className="w-3 h-3 mr-0.5" />
                      {ev.assigned_unit ? ev.assigned_unit.name.split(' ')[0] : 'En Route'}
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
