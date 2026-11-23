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

const API_BASE = import.meta.env.VITE_API_BASE || '';
const WS_URL = import.meta.env.VITE_WS_URL || (typeof window !== 'undefined' 
  ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws` 
  : 'ws://localhost:8000/ws');

// Pure Web Audio API tactical crisis beep
const playTacticalBeep = (freq = 880, duration = 0.15) => {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
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
  } catch (e) {
    // Audio context may require user gesture on first interaction
  }
};

export default function App() {
  const [currentView, setCurrentView] = useState('command'); // 'command' | 'citizen'
  const [events, setEvents] = useState([]);
  const [units, setUnits] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [latencyMs, setLatencyMs] = useState(38);
  const [isPhoneModalOpen, setIsPhoneModalOpen] = useState(false);
  const [isPitchDeckOpen, setIsPitchDeckOpen] = useState(false);
  const [isResponderModalOpen, setIsResponderModalOpen] = useState(false);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  const wsRef = useRef(null);
  const pingIntervalRef = useRef(null);

  // Initialize WebSocket Connection (FR-3.1 Real-Time Streaming)
  const connectWebSocket = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[RESCUENET-X WS] Connected to backend stream');
        setWsConnected(true);

        // Periodic ping for keepalive and latency measurement
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            const start = performance.now();
            ws.send('ping');
            setLatencyMs(Math.round(performance.now() - start + 25));
          }
        }, 8000);
      };

      ws.onmessage = (messageEvent) => {
        try {
          if (messageEvent.data === 'pong') return;

          const data = JSON.parse(messageEvent.data);

          if (data.type === 'INITIAL_STATE') {
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

            // If selected event was updated
            setSelectedEvent((prev) => (prev && prev.id === newEvent.id ? newEvent : prev));
          } else if (data.type === 'DISPATCH_CONFIRMED') {
            setEvents((prev) =>
              prev.map((e) =>
                e.id === data.event_id
                  ? { ...e, status: 'DISPATCHED', assigned_unit: data.unit }
                  : e
              )
            );
          }
        } catch (err) {
          console.error('[WS Parse Error]:', err);
        }
      };

      ws.onclose = () => {
        console.log('[RESCUENET-X WS] Disconnected. Retrying in 3s...');
        setWsConnected(false);
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (err) => {
        console.warn('[WS Error]:', err);
        ws.close();
      };
    } catch (e) {
      console.error('[WS Init Error]:', e);
      setTimeout(connectWebSocket, 4000);
    }
  }, []);

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
    };
  }, [connectWebSocket]);

  // FR-3.3: 1-Click Dispatch Action
  const handleDispatch = async (eventId) => {
    playTacticalBeep(1100, 0.2);
    try {
      const response = await authFetch(`${API_BASE}/api/dispatch/${eventId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_id: eventId })
      });
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

  // Resolve Incident Action (frees assigned unit)
  const handleResolve = async (eventId) => {
    try {
      const response = await authFetch(`${API_BASE}/api/events/${eventId}/resolve`, {
        method: 'POST'
      });
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

  // Trigger Demo Disaster Scenario (Flood, Medical, Fire)
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

  // Upload Visual Incident Photo (YOLO & pHash)
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
      await authFetch(`${API_BASE}/api/simulate/reset`, { method: 'POST' });
      setEvents([]);
      setSelectedEvent(null);
      // Reload baseline
      const resUn = await fetch(`${API_BASE}/api/units`).then((r) => r.json());
      if (resUn.units) setUnits(resUn.units);
    } catch (e) {
      console.error('Reset failed:', e);
    }
  };

  if (currentView === 'citizen') {
    return <CitizenPortal onBackToCommand={() => setCurrentView('command')} />;
  }

  return (
    <div className="flex flex-col h-screen w-screen bg-[#0a0e17] text-slate-100 overflow-hidden font-sans">
      {/* 1. Header with KPIs and Connection State */}
      <HeaderStats
        events={events}
        units={units}
        wsConnected={wsConnected}
        latencyMs={latencyMs}
        onOpenCitizenPortal={() => setCurrentView('citizen')}
        onOpenPhoneSimulator={() => setIsPhoneModalOpen(true)}
        onOpenPitchDeck={() => setIsPitchDeckOpen(true)}
        onOpenResponderTerminal={() => setIsResponderModalOpen(true)}
        onOpenApiKeys={() => setIsApiKeyModalOpen(true)}
      />

      {/* 2. Main Content Split: GIS Map + Incident Feed Sidebar */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden relative">
        {/* Interactive GIS Map (Mapbox GL with Leaflet fallback) */}
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
