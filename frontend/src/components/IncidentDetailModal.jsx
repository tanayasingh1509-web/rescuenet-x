import React, { useState, useEffect } from 'react';
import {
  X, AlertTriangle, CheckCircle2,
  Volume2, Play, Pause, Navigation, Phone,
  Clock, Truck, MapPin, Hash, FileText, Check
} from 'lucide-react';

export default function IncidentDetailModal({
  event,
  onClose,
  onDispatch,
  onResolve
}) {
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        window.speechSynthesis.cancel();
        onClose();
      }
    };
    if (event) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [event, onClose]);

  // Never render the dialog (and its full-screen black backdrop) for a missing
  // or malformed event.
  if (!event || !event.id) return null;

  const isCritical = event.severity >= 8;
  const isDispatched = event.status === 'DISPATCHED';
  const isResolved = event.status === 'RESOLVED';

  // Audio speech synthesis simulation
  const toggleAudioPlayback = () => {
    if ('speechSynthesis' in window) {
      if (isPlayingAudio) {
        window.speechSynthesis.cancel();
        setIsPlayingAudio(false);
      } else {
        const textToSpeak = event.raw_transcript || event.summary || "Emergency incident report.";
        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        utterance.rate = 1.0;
        utterance.pitch = 0.9;
        utterance.onend = () => setIsPlayingAudio(false);
        utterance.onerror = () => setIsPlayingAudio(false);
        window.speechSynthesis.speak(utterance);
        setIsPlayingAudio(true);
      }
    } else {
      alert("Browser speech synthesis not supported.");
    }
  };

  // Two-tier Verification Badge helper (FR-2.1)
  const renderVerificationBadge = () => {
    if (event.confidence >= 0.85) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-[#032e22] text-emerald-300 border border-emerald-800">
          <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-400" />
          Verified Auto-Dispatch ({(event.confidence * 100).toFixed(0)}% &ge; 85%)
        </span>
      );
    } else if (event.confidence >= 0.70) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-[#381e05] text-amber-300 border border-amber-800">
          <AlertTriangle className="w-3 h-3 mr-1 text-amber-400" />
          Unverified / Low-Confidence ({(event.confidence * 100).toFixed(0)}%)
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-[#38090f] text-rose-300 border border-rose-800">
          <AlertTriangle className="w-3 h-3 mr-1 text-rose-400" />
          Manual Operator Review Required (&lt; 70%)
        </span>
      );
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-incident-title"
      className="fixed inset-0 z-[2000] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
    >
      <div className="bg-[#0c121e] border border-[#25354e] w-full max-w-xl rounded shadow-2xl overflow-hidden flex flex-col max-h-[90vh] text-slate-100">
        {/* Dossier Header */}
        <div className="bg-[#090d16] p-3.5 border-b border-[#1f2b3e] flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <span className={`px-2 py-0.5 rounded text-[11px] font-extrabold font-mono uppercase tracking-wider ${
              isCritical ? 'bg-rose-950 text-rose-300 border border-rose-800' : 'bg-amber-950 text-amber-300 border border-amber-800'
            }`}>
              {event.category}
            </span>
            <div>
              <h2 id="modal-incident-title" className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <span>{event.sector || 'Incident Locus'}</span>
                <span className="text-xs text-slate-400 font-mono select-text">#{event.id}</span>
              </h2>
              <div className="flex items-center space-x-2 mt-0.5 text-[11px] text-slate-400">
                <MapPin className="w-3 h-3 text-slate-400" />
                <span className="font-mono select-text">
                  {event.coordinates ? `${event.coordinates.lat.toFixed(4)}, ${event.coordinates.lng.toFixed(4)}` : 'N/A'}
                </span>
                <span>•</span>
                <span>Channel: <strong className="uppercase text-slate-300 font-mono">{event.source}</strong></span>
              </div>
            </div>
          </div>

          <button
            onClick={() => {
              window.speechSynthesis.cancel();
              onClose();
            }}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-[#192436] transition focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Close Incident Dossier"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Dossier Content */}
        <div className="p-4 overflow-y-auto space-y-3.5 text-xs select-text">
          {/* Key Incident Telemetry Strip */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#101726] p-2.5 rounded border border-[#1e2a3c] text-center">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Priority / Urgency</span>
              <span className={`text-lg font-bold font-mono ${isCritical ? 'text-rose-400' : 'text-amber-400'}`}>
                {event.severity} <span className="text-xs text-slate-400">/ 10</span>
              </span>
            </div>
            <div className="bg-[#101726] p-2.5 rounded border border-[#1e2a3c] text-center">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Casualties</span>
              <span className="text-lg font-bold font-mono text-slate-100">
                {event.casualty_count}
              </span>
            </div>
            <div className="bg-[#101726] p-2.5 rounded border border-[#1e2a3c] text-center">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">AI Confidence</span>
              <span className="text-lg font-bold font-mono text-sky-400">
                {(event.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Verification Status Tier */}
          <div className="flex items-center justify-between bg-[#101726] px-3 py-2 rounded border border-[#1e2a3c]">
            <span className="text-slate-400 font-medium text-[11px]">Verification Status:</span>
            {renderVerificationBadge()}
          </div>

          {/* Tactical Operational Summary */}
          <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] space-y-1">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono flex items-center">
              <FileText className="w-3.5 h-3.5 text-slate-400 mr-1.5" />
              Tactical Operational Briefing
            </span>
            <p className="text-slate-200 leading-relaxed font-sans text-xs pt-0.5">
              {event.summary}
            </p>
          </div>

          {/* Raw Audio Transcript / Playback */}
          {event.raw_transcript && (
            <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono flex items-center">
                  <Volume2 className="w-3.5 h-3.5 text-cyan-400 mr-1.5" />
                  Whisper Voice Transmission
                </span>
                <button
                  onClick={toggleAudioPlayback}
                  className="flex items-center space-x-1.5 bg-[#142134] text-cyan-300 hover:bg-[#1b2d47] border border-[#273d5e] px-2 py-0.5 rounded text-[11px] font-semibold transition"
                  aria-label="Toggle voice transcript speech playback"
                >
                  {isPlayingAudio ? (
                    <>
                      <Pause className="w-3 h-3 text-cyan-400" />
                      <span>Pause Audio</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3 text-cyan-400" />
                      <span>Play Transmission</span>
                    </>
                  )}
                </button>
              </div>
              <p className="text-slate-300 italic bg-[#090d16] p-2.5 rounded border border-[#1a2538] text-[11px] leading-relaxed">
                "{event.raw_transcript}"
              </p>
            </div>
          )}

          {/* Perceptual Hash / Deduplication Info */}
          {event.phash && (
            <div className="flex items-center justify-between bg-[#101726] px-3 py-2 rounded border border-[#1e2a3c] font-mono text-[11px]">
              <span className="text-slate-400 flex items-center">
                <Hash className="w-3 h-3 text-indigo-400 mr-1.5" />
                Image Perceptual Hash:
              </span>
              <span className="text-indigo-300 select-text">{event.phash}</span>
            </div>
          )}

          {/* Assigned CAD Rescue Unit Routing */}
          <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono flex items-center">
                <Truck className="w-3.5 h-3.5 text-emerald-400 mr-1.5" />
                CAD Unit Routing & Deployment
              </span>
              <span className={`text-[10px] font-bold font-mono px-1.5 py-0.5 rounded ${
                isResolved
                  ? 'bg-slate-800 text-slate-300 border border-slate-700'
                  : isDispatched
                  ? 'bg-[#032e22] text-emerald-300 border border-emerald-800'
                  : 'bg-[#291e0a] text-amber-300 border border-amber-800'
              }`}>
                {isResolved ? 'RESOLVED' : isDispatched ? 'EN ROUTE' : 'ALLOCATED'}
              </span>
            </div>

            {event.assigned_unit ? (
              <div className="grid grid-cols-2 gap-2 text-slate-300 pt-1">
                <div>
                  <span className="text-slate-400 block text-[10px]">UNIT NAME</span>
                  <span className="font-semibold text-slate-100">{event.assigned_unit.name}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">RESPONSE ETA</span>
                  <span className="font-semibold text-emerald-300 flex items-center font-mono">
                    <Clock className="w-3 h-3 mr-1" />
                    ~{event.assigned_unit.eta_minutes || 4} mins
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">DISTANCE</span>
                  <span className="font-semibold text-slate-200 font-mono">
                    {event.assigned_unit.distance_km ? `${event.assigned_unit.distance_km} km` : '1.4 km'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">RADIO / PHONE</span>
                  <span className="font-semibold text-slate-200 flex items-center font-mono">
                    <Phone className="w-3 h-3 mr-1 text-slate-400" />
                    {event.assigned_unit.contact}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-amber-400 text-[11px]">
                No unit assigned. Authorize CAD Dispatch below to alert nearest response squad.
              </p>
            )}
          </div>
        </div>

        {/* Action Footer */}
        <div className="p-3 bg-[#090d16] border-t border-[#1f2b3e] flex items-center justify-between">
          <div className="text-[11px] text-slate-400 font-mono">
            {isResolved ? (
              <span className="text-slate-400 flex items-center">
                <Check className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                Incident Resolved • Unit Available
              </span>
            ) : isDispatched ? (
              <span className="text-emerald-400 flex items-center">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                Unit Dispatched (CAD Alert Broadcasted)
              </span>
            ) : (
              <span>Ready for immediate emergency action</span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => {
                window.speechSynthesis.cancel();
                onClose();
              }}
              className="px-3 py-1.5 rounded bg-[#162030] hover:bg-[#1e2c42] text-slate-300 font-medium text-xs transition"
            >
              Dismiss
            </button>

            {isDispatched && onResolve && (
              <button
                onClick={() => {
                  onResolve(event.id);
                  onClose();
                }}
                className="px-3 py-1.5 rounded bg-emerald-800 hover:bg-emerald-700 text-white font-bold text-xs flex items-center space-x-1 transition active:scale-95"
                aria-label="Resolve Incident and Free Response Unit"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Resolve Incident</span>
              </button>
            )}

            {!isDispatched && !isResolved && (
              <button
                onClick={() => {
                  onDispatch(event.id);
                  onClose();
                }}
                className="px-3.5 py-1.5 rounded bg-rose-700 hover:bg-rose-600 text-white font-bold text-xs flex items-center space-x-1.5 transition active:scale-95 focus-visible:ring-2 focus-visible:ring-rose-500"
                aria-label="Authorize CAD Dispatch"
              >
                <Navigation className="w-3.5 h-3.5" />
                <span>Authorize CAD Dispatch</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
