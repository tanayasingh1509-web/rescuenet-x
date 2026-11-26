import React, { useState, useEffect, useRef, useCallback } from 'react';
import HeaderStats from './components/HeaderStats';
import GISMap from './components/GISMap';
import IncidentFeed from './components/IncidentFeed';
import IncidentDetailModal from './components/IncidentDetailModal';
import SimulationBar from './components/SimulationBar';
import CitizenPortal from './components/CitizenPortal';
import PhoneSimulatorModal from './components/PhoneSimulatorModal';
import PitchDeckModal from './components/PitchDeckModal';
import ResponderTerminalModal from './components/ResponderTerminalModal';
import ApiKeyModal from './components/ApiKeyModal';
import { authFetch } from './utils/auth';
import { WifiOff } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || (typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.host}`
  : '');
const WS_URL = import.meta.env.VITE_WS_URL || (typeof window !== 'undefined'
  ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
  : '');

// Single shared AudioContext singleton to prevent "more than 6 AudioContexts" browser warnings
let sharedAudioContext = null;
const getSharedAudioContext = () => {
  if (typeof window === 'undefined') return null;
  if (!sharedAudioContext) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) sharedAudioContext = new AudioCtx();
  }
  if (sharedAudioContext && sharedAudioContext.state === 'suspended') {
    sharedAudioContext.resume().catch(() => {});
  }
  return sharedAudioContext;
};

// Pure Web Audio API tactical crisis beep using shared context
const playTacticalBeep = (freq = 880, duration = 0.15) => {
  try {
    const ctx = getSharedAudioContext();
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  } catch {
    // Audio context may require user gesture on first interaction
  }
};

export default function App() {
  // Hash-based routing (#/command, #/citizen)
  const getInitialView = () => {
    if (typeof window !== 'undefined' && window.location.hash === '#/citizen') {
      return 'citizen';
    }
    return 'command';
  };

  const [currentView, setCurrentView] = useState(getInitialView);
  const [events, setEvents] = useState([]);
  const [units, setUnits] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [wsReconnectCountdown, setWsReconnectCountdown] = useState(0);
  const [latencyMs, setLatencyMs] = useState(0);

  const [isPhoneModalOpen, setIsPhoneModalOpen] = useState(false);
  const [isPitchDeckOpen, setIsPitchDeckOpen] = useState(false);
  const [isResponderModalOpen, setIsResponderModalOpen] = useState(false);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  const [actionError, setActionError] = useState(null);

  const showActionError = (msg) => {
    console.error('[Action Error]:', msg);
    setActionError(msg);
    if (typeof window !== 'undefined' && typeof window.alert === 'function') {
      try {
        window.alert(msg);
      } catch (_) {}
    }
  };

  const wsRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const pingStartTimeRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const reconnectIntervalTimerRef = useRef(null);
  const backoffDelayRef = useRef(1000); // 1s -> 2s -> 4s ... max 15s
  const connectWsRef = useRef(null);

  // Synchronize hash routing with currentView
  const navigateView = (view) => {
    setCurrentView(view);
    if (typeof window !== 'undefined') {
      window.location.hash = view === 'citizen' ? '#/citizen' : '#/command';
    }
  };

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash;
      if (hash === '#/citizen') {
        setCurrentView('citizen');
      } else {
        setCurrentView('command');
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Initialize WebSocket Connection with Exponential Backoff
  const connectWebSocket = useCallback(() => {
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    if (reconnectIntervalTimerRef.current) clearInterval(reconnectIntervalTimerRef.current);

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[RESCUENET-X WS] Connected to backend telemetry stream');
        setWsConnected(true);
        setWsReconnectCountdown(0);
        backoffDelayRef.current = 1000; // Reset exponential backoff on successful connect

        // Periodic ping for keepalive and real latency roundtrip measurement
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            pingStartTimeRef.current = performance.now();
            ws.send('ping');
          }
        }, 5000);
      };

      ws.onmessage = (messageEvent) => {
        try {
          // Check for plain pong or json pong
          if (messageEvent.data === 'pong') {
            if (pingStartTimeRef.current > 0) {
              const rtt = Math.max(1, Math.round(performance.now() - pingStartTimeRef.current));
              setLatencyMs(rtt);
            }
            return;
          }

          const data = JSON.parse(messageEvent.data);

          if (data.type === 'pong') {
            if (pingStartTimeRef.current > 0) {
              const rtt = Math.max(1, Math.round(performance.now() - pingStartTimeRef.current));
              setLatencyMs(rtt);
            }
          } else if (data.type === 'INITIAL_STATE') {
            if (data.events) setEvents(data.events);
            if (data.units) setUnits(data.units);
          } else if (data.type === 'INCIDENT_UPDATE') {
            const newEvent = data.payload;
            playTacticalBeep(newEvent.severity >= 8 ? 960 : 720);

            setEvents((prev) => {
              const existingIdx = prev.findIndex((e) => e.id === newEvent.id);
              if (existingIdx >= 0) {
                const updated = [...prev];
                updated[existingIdx] = newEvent;
                return updated;
              }
              return [newEvent, ...prev];
            });

            setSelectedEvent((prev) => (prev && prev.id === newEvent.id ? newEvent : prev));
          } else if (data.type === 'UNIT_UPDATE') {
            const updatedUnit = data.payload;
            setUnits((prev) =>
              prev.map((u) => (u.id === updatedUnit.id ? updatedUnit : u))
            );
          } else if (data.type === 'DISPATCH_CONFIRMED') {
            setEvents((prev) =>
              prev.map((e) =>
                e.id === data.event_id
                  ? { ...e, status: 'DISPATCHED', assigned_unit: data.unit }
                  : e
              )
            );
            if (data.unit) {
              setUnits((prev) =>
                prev.map((u) => (u.id === data.unit.id ? data.unit : u))
              );
            }
          }
        } catch (err) {
          console.error('[WS Parse Error]:', err);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);

        const currentDelay = backoffDelayRef.current;
        const nextDelay = Math.min(currentDelay * 2, 15000);
        backoffDelayRef.current = nextDelay;

        let secondsRemaining = Math.ceil(currentDelay / 1000);
        setWsReconnectCountdown(secondsRemaining);

        reconnectIntervalTimerRef.current = setInterval(() => {
          secondsRemaining -= 1;
          setWsReconnectCountdown((prev) => Math.max(0, prev - 1));
          if (secondsRemaining <= 0) {
            clearInterval(reconnectIntervalTimerRef.current);
          }
        }, 1000);

        reconnectTimeoutRef.current = setTimeout(() => {
          connectWsRef.current?.();
        }, currentDelay);
      };

      ws.onerror = (err) => {
        console.warn('[WS Error]:', err);
        ws.close();
      };
    } catch (e) {
      console.error('[WS Init Error]:', e);
      reconnectTimeoutRef.current = setTimeout(() => {
        connectWsRef.current?.();
      }, 3000);
    }
  }, []);

  useEffect(() => {
    connectWsRef.current = connectWebSocket;
  }, [connectWebSocket]);

  useEffect(() => {
    // Initial REST state fetch
    const fetchInitialData = async () => {
      try {
        const [resEv, resUn] = await Promise.all([
          fetch(`${API_BASE}/api/events`).then((r) => r.json()),
          fetch(`${API_BASE}/api/units`).then((r) => r.json())
        ]);
        if (resEv.events) setEvents(resEv.events);
        if (resUn.units) setUnits(resUn.units);
      } catch (e) {
        console.warn('Initial REST load failed, will rely on WebSocket:', e);
      }
    };

    fetchInitialData();
    connectWebSocket();

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (reconnectIntervalTimerRef.current) clearInterval(reconnectIntervalTimerRef.current);
    };
  }, [connectWebSocket]);

  // Surface failed operator actions instead of failing silently
  const reportActionError = (label, response) => {
    const msg =
      response.status === 401
        ? `${label}: operator token missing or invalid`
        : `${label} failed (HTTP ${response.status})`;
    console.error(msg);
    setActionError(msg);
    if (typeof window !== 'undefined') window.alert(msg);
  };

  // 1-Click Dispatch Action
  const handleDispatch = async (eventId) => {
    playTacticalBeep(1100, 0.2);
    try {
      const response = await authFetch(`${API_BASE}/api/dispatch/${eventId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_id: eventId })
      });
      if (!response.ok) {
        reportActionError('Dispatch', response);
        return;
      }
      const data = await response.json();
      if (data.status === 'dispatched') {
        setEvents((prev) =>
          prev.map((e) =>
            e.id === eventId
              ? { ...e, status: 'DISPATCHED', assigned_unit: data.assigned_unit }
              : e
          )
        );
        if (selectedEvent && selectedEvent.id === eventId) {
          setSelectedEvent((prev) => ({
            ...prev,
            status: 'DISPATCHED',
            assigned_unit: data.assigned_unit
          }));
        }
      }
    } catch (e) {
      console.error('Dispatch failed:', e);
    }
  };

  // Resolve Incident Action (frees assigned unit back to AVAILABLE)
  const handleResolve = async (eventId) => {
    try {
      const response = await authFetch(`${API_BASE}/api/events/${eventId}/resolve`, {
        method: 'POST'
      });
      if (!response.ok) {
        reportActionError('Resolve incident', response);
        return;
      }
      const data = await response.json();
      if (data.status === 'resolved') {
        setEvents((prev) =>
          prev.map((e) => (e.id === eventId ? { ...e, status: 'RESOLVED' } : e))
        );
        if (selectedEvent && selectedEvent.id === eventId) {
          setSelectedEvent((prev) => ({ ...prev, status: 'RESOLVED' }));
        }
      }
    } catch (e) {
      console.error('Resolve incident failed:', e);
    }
  };

  // Trigger Demo Disaster Scenario
  const handleTriggerScenario = async (scenarioName) => {
    try {
      const res = await fetch(`${API_BASE}/api/simulate/scenario/${scenarioName}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.event) {
        setSelectedEvent(data.event);
      }
    } catch (e) {
      console.error('Scenario trigger failed:', e);
    }
  };

  // Simulate Voice Telephony Input
  const handleSimulateVoice = async (text) => {
    try {
      const formData = new FormData();
      formData.append('transcript_text', text);
      const res = await fetch(`${API_BASE}/api/simulate/voice`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.event) {
        setSelectedEvent(data.event);
      }
    } catch (e) {
      console.error('Voice simulation failed:', e);
    }
  };

  // Upload Visual Incident Photo
  const handleUploadImage = async (file) => {
    try {
      const formData = new FormData();
      formData.append('image', file);
      formData.append('sector', 'Drone Reconnaissance Sector');
      const res = await fetch(`${API_BASE}/api/report/visual`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.event) {
        setSelectedEvent(data.event);
      }
    } catch (e) {
      console.error('Image upload failed:', e);
    }
  };

  // Reset demo store
  const handleReset = async () => {
    try {
      const response = await authFetch(`${API_BASE}/api/simulate/reset`, { method: 'POST' });
      if (!response.ok) {
        reportActionError('Reset', response);
        return;
      }
      setEvents([]);
      setSelectedEvent(null);
      const resUn = await fetch(`${API_BASE}/api/units`).then((r) => r.json());
      if (resUn.units) setUnits(resUn.units);
    } catch (e) {
      console.error('Reset failed:', e);
    }
  };

  if (currentView === 'citizen') {
    return <CitizenPortal onBackToCommand={() => navigateView('command')} />;
  }

  return (
    <div className="flex flex-col h-screen w-screen bg-[#0a0e17] text-slate-100 overflow-hidden font-sans">
      {/* Disconnection Alert Banner */}
      {!wsConnected && (
        <div
          role="alert"
          className="bg-amber-950/90 border-b border-amber-700/80 px-4 py-1.5 text-xs text-amber-200 flex items-center justify-between font-mono z-[6000]"
        >
          <div className="flex items-center space-x-2">
            <WifiOff className="w-4 h-4 text-amber-400 animate-pulse" />
            <span>
              STREAM DISCONNECTED: Reconnecting in {wsReconnectCountdown > 0 ? `${wsReconnectCountdown}s` : 'a moment'}...
            </span>
          </div>
          <button
            onClick={() => connectWebSocket()}
            className="text-[10px] bg-amber-900 hover:bg-amber-800 text-amber-100 px-2 py-0.5 rounded border border-amber-600 transition"
          >
            Retry Now
          </button>
        </div>
      )}

      {/* Action Error Alert Banner */}
      {actionError && (
        <div
          role="alert"
          className="bg-rose-950/90 border-b border-rose-700/80 px-4 py-1.5 text-xs text-rose-200 flex items-center justify-between font-mono z-[6000]"
        >
          <div className="flex items-center space-x-2">
            <span className="font-bold text-rose-400">[OPERATOR ERROR]:</span>
            <span>{actionError}</span>
          </div>
          <button
            onClick={() => setActionError(null)}
            className="text-[10px] bg-rose-900 hover:bg-rose-800 text-rose-100 px-2 py-0.5 rounded border border-rose-600 transition"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 1. Header with KPIs and Connection State */}
      <HeaderStats
        events={events}
        units={units}
        wsConnected={wsConnected}
        latencyMs={latencyMs}
        onOpenCitizenPortal={() => navigateView('citizen')}
        onOpenPhoneSimulator={() => setIsPhoneModalOpen(true)}
        onOpenPitchDeck={() => setIsPitchDeckOpen(true)}
        onOpenResponderTerminal={() => setIsResponderModalOpen(true)}
        onOpenApiKeys={() => setIsApiKeyModalOpen(true)}
      />

      {/* 2. Main Content Split: GIS Map + Incident Feed Sidebar */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden relative">
        {/* Interactive GIS Map */}
        <section className="flex-1 h-full p-2.5 flex flex-col min-h-0">
          <GISMap
            events={events}
            units={units}
            selectedEvent={selectedEvent}
            onSelectEvent={setSelectedEvent}
            onDispatch={handleDispatch}
          />
        </section>

        {/* Live Incident Stream Feed */}
        <IncidentFeed
          events={events}
          selectedEvent={selectedEvent}
          onSelectEvent={setSelectedEvent}
          onDispatch={handleDispatch}
        />
      </main>

      {/* 3. Bottom Demo & Simulation Bar */}
      <SimulationBar
        onTriggerScenario={handleTriggerScenario}
        onSimulateVoice={handleSimulateVoice}
        onUploadImage={handleUploadImage}
        onReset={handleReset}
      />

      {/* 4. Incident Detail Modal / Inspection Popup */}
      <IncidentDetailModal
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        onDispatch={handleDispatch}
        onResolve={handleResolve}
      />

      {/* 5. 2G Telephony Phone & IVR Simulator Modal */}
      <PhoneSimulatorModal
        isOpen={isPhoneModalOpen}
        onClose={() => setIsPhoneModalOpen(false)}
      />

      {/* 6. Pitch Deck & Presentation Slides Modal */}
      <PitchDeckModal
        isOpen={isPitchDeckOpen}
        onClose={() => setIsPitchDeckOpen(false)}
      />

      {/* 7. Tactical Field Responder Radio Terminal Modal */}
      <ResponderTerminalModal
        isOpen={isResponderModalOpen}
        onClose={() => setIsResponderModalOpen(false)}
        units={units}
        events={events}
      />

      {/* 8. API Credentials & Cloud Integration Modal */}
      <ApiKeyModal
        isOpen={isApiKeyModalOpen}
        onClose={() => setIsApiKeyModalOpen(false)}
      />
    </div>
  );
}
