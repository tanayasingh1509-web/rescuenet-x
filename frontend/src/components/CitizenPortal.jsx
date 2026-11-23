import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertOctagon, Waves, Flame, HeartPulse, ShieldAlert,
  LifeBuoy, MapPin, Camera, Send, CheckCircle2,
  ArrowLeft, Loader2, Radio, WifiOff, RefreshCw
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || '';
const OUTBOX_STORAGE_KEY = 'rescuenet_offline_outbox';

export default function CitizenPortal({ onBackToCommand }) {
  const [category, setCategory] = useState('FLOOD');
  const [sector, setSector] = useState('Citizen Hotspot Node B');
  const [description, setDescription] = useState('');
  const [casualtyCount, setCasualtyCount] = useState(1);
  const [lat, setLat] = useState(null);
  const [lng, setLng] = useState(null);
  const [gpsStatus, setGpsStatus] = useState('acquiring'); // 'acquiring' | 'ready' | 'denied' | 'unsupported'
  const [gpsAccuracy, setGpsAccuracy] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedEvent, setSubmittedEvent] = useState(null);
  const [outboxCount, setOutboxCount] = useState(0);
  const [isFlushingOutbox, setIsFlushingOutbox] = useState(false);
  const [outboxSuccessNotice, setOutboxSuccessNotice] = useState(null);

  // Helper: Request GPS coordinates from device
  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setGpsStatus('unsupported');
      // Fallback to default emergency center coordinates
      setLat(28.6145);
      setLng(77.2085);
      return;
    }

    setGpsStatus('acquiring');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude);
        setLng(pos.coords.longitude);
        setGpsAccuracy(Math.round(pos.coords.accuracy || 10));
        setGpsStatus('ready');
      },
      (err) => {
        console.warn('Geolocation denied or failed:', err);
        setGpsStatus('denied');
        // Fallback default coordinates so user is not permanently stuck
        setLat(28.6145);
        setLng(77.2085);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
    );
  }, []);

  // Offline Outbox management
  const getOutbox = useCallback(() => {
    try {
      const raw = localStorage.getItem(OUTBOX_STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }, []);

  const saveOutbox = useCallback((items) => {
    try {
      localStorage.setItem(OUTBOX_STORAGE_KEY, JSON.stringify(items));
      setOutboxCount(items.length);
    } catch (e) {
      console.error('Failed to save offline outbox:', e);
    }
  }, []);

  const queueSubmission = useCallback((payload, isVisual = false) => {
    const items = getOutbox();
    const entry = {
      id: `outbox_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      timestamp: new Date().toISOString(),
      isVisual,
      payload
    };
    items.push(entry);
    saveOutbox(items);
  }, [getOutbox, saveOutbox]);

  const flushOutbox = useCallback(async () => {
    const items = getOutbox();
    if (items.length === 0 || isFlushingOutbox || !navigator.onLine) return;

    setIsFlushingOutbox(true);
    const remaining = [];
    let synced = 0;

    for (const item of items) {
      try {
        const res = await fetch(`${API_BASE}/api/report/pwa`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(item.payload)
        });
        if (res.ok) {
          synced += 1;
        } else {
          remaining.push(item);
        }
      } catch {
        remaining.push(item);
      }
    }

    saveOutbox(remaining);
    setIsFlushingOutbox(false);
    if (synced > 0) {
      setOutboxSuccessNotice(`Successfully synced ${synced} queued offline report(s).`);
      setTimeout(() => setOutboxSuccessNotice(null), 5000);
    }
  }, [getOutbox, isFlushingOutbox, saveOutbox]);

  // On mount: Auto-request GPS & listen for online outbox flush
  useEffect(() => {
    requestLocation();
    const currentOutbox = getOutbox();
    setOutboxCount(currentOutbox.length);

    const handleOnline = () => {
      flushOutbox();
    };

    window.addEventListener('online', handleOnline);
    if (navigator.onLine && currentOutbox.length > 0) {
      flushOutbox();
    }

    return () => {
      window.removeEventListener('online', handleOnline);
    };
  }, [requestLocation, getOutbox, flushOutbox]);

  const isLocationValid =
    typeof lat === 'number' &&
    typeof lng === 'number' &&
    !isNaN(lat) &&
    !isNaN(lng) &&
    lat >= -90 &&
    lat <= 90 &&
    lng >= -180 &&
    lng <= 180;

  // Handle detailed form submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isLocationValid) return;
    setIsSubmitting(true);

    const payload = {
      category,
      lat,
      lng,
      sector: sector || 'Citizen Visual SOS',
      casualty_count: parseInt(casualtyCount, 10) || 0,
      severity: 8,
      description: description || `Citizen reported ${category} emergency.`
    };

    try {
      if (imageFile) {
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('lat', lat.toString());
        formData.append('lng', lng.toString());
        formData.append('sector', sector || 'Citizen Visual SOS');
        const res = await fetch(`${API_BASE}/api/report/visual`, {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        setSubmittedEvent(data.event);
      } else {
        const res = await fetch(`${API_BASE}/api/report/pwa`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        setSubmittedEvent(data.event);
      }
    } catch (err) {
      console.warn('Network transmission error, queuing to offline outbox:', err);
      queueSubmission(payload, false);
      setSubmittedEvent({
        id: 'OFFLINE_QUEUED',
        category: payload.category,
        status: 'QUEUED_OFFLINE',
        sector: payload.sector,
        summary: 'Report queued in offline outbox. Will automatically dispatch when connection restores.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle 1-tap SOS distress beacon
  const handleInstantSOS = async () => {
    if (!isLocationValid) return;
    setIsSubmitting(true);

    const payload = {
      category: 'RESCUE',
      lat,
      lng,
      sector: sector || 'CRITICAL INSTANT SOS BEACON',
      casualty_count: 1,
      severity: 10,
      description: 'INSTANT SOS BEACON ACTIVATED! Immediate search & rescue response required.'
    };

    try {
      const res = await fetch(`${API_BASE}/api/report/pwa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setSubmittedEvent(data.event);
    } catch (err) {
      console.warn('SOS network error, saving to offline outbox:', err);
      queueSubmission(payload, false);
      setSubmittedEvent({
        id: 'OFFLINE_QUEUED',
        category: 'RESCUE',
        status: 'QUEUED_OFFLINE',
        sector: payload.sector,
        summary: 'SOS Beacon queued locally in offline outbox. Auto-dispatch will trigger when back online.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e17] text-slate-100 flex flex-col items-center p-3 sm:p-5 font-sans">
      {/* Top Banner Navigation & Status */}
      <div className="w-full max-w-lg flex items-center justify-between py-2 border-b border-[#1b2537] mb-4">
        <button
          onClick={onBackToCommand}
          className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-white transition font-medium focus-visible:ring-2 focus-visible:ring-blue-500 rounded p-1"
          aria-label="Return to CAD Command Center"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to CAD Command</span>
        </button>

        <div className="flex items-center space-x-2">
          {outboxCount > 0 && (
            <button
              onClick={flushOutbox}
              disabled={isFlushingOutbox}
              className="text-[10px] font-mono bg-amber-950/80 text-amber-300 border border-amber-800 px-2 py-0.5 rounded flex items-center space-x-1 hover:bg-amber-900 transition"
              title="Click to flush queued offline reports"
            >
              <WifiOff className="w-3 h-3 text-amber-400" />
              <span>OUTBOX: {outboxCount}</span>
              {isFlushingOutbox && <RefreshCw className="w-3 h-3 animate-spin ml-1" />}
            </button>
          )}

          <span className="text-[10px] font-mono bg-[#0f231d] text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded flex items-center">
            <Radio className="w-3 h-3 mr-1 text-emerald-400" />
            OFFLINE PWA READY
          </span>
        </div>
      </div>

      {outboxSuccessNotice && (
        <div role="alert" className="w-full max-w-lg mb-3 p-2.5 rounded bg-emerald-950/80 border border-emerald-700 text-emerald-200 text-xs flex items-center space-x-2 font-mono">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{outboxSuccessNotice}</span>
        </div>
      )}

      <div className="w-full max-w-lg bg-[#0c121e] border border-[#25354e] rounded p-5 space-y-5">
        {/* Title */}
        <div className="text-center space-y-1">
          <div className="flex items-center justify-center space-x-2">
            <AlertOctagon className="w-5 h-5 text-rose-500" />
            <h1 className="text-base font-bold tracking-wider text-slate-100 font-mono">
              CITIZEN EMERGENCY SOS
            </h1>
          </div>
          <p className="text-xs text-slate-400 max-w-xs mx-auto">
            Low-bandwidth civil distress portal. Operates over local hotspot mesh, cellular, or satellite data.
          </p>
        </div>

        {/* Live GPS Telemetry Status Bar */}
        <div className={`p-2.5 rounded border text-xs font-mono flex items-center justify-between ${
          gpsStatus === 'ready'
            ? 'bg-[#0a1f18] border-emerald-800/80 text-emerald-300'
            : gpsStatus === 'acquiring'
            ? 'bg-[#1e1b10] border-amber-800/80 text-amber-300'
            : 'bg-[#261014] border-rose-800/80 text-rose-300'
        }`}>
          <div className="flex items-center space-x-2">
            <MapPin className={`w-4 h-4 ${
              gpsStatus === 'ready' ? 'text-emerald-400' : gpsStatus === 'acquiring' ? 'text-amber-400 animate-pulse' : 'text-rose-400'
            }`} />
            <div>
              <div className="font-bold uppercase tracking-wider text-[11px]">
                {gpsStatus === 'ready' && `GPS ACQUIRED (±${gpsAccuracy || 10}m)`}
                {gpsStatus === 'acquiring' && 'ACQUIRING DEVICE GPS...'}
                {gpsStatus === 'denied' && 'GPS DENIED (USING MANUAL/SECTOR)'}
                {gpsStatus === 'unsupported' && 'GPS UNSUPPORTED (USING SECTOR)'}
              </div>
              <div className="text-[10px] text-slate-300 select-text">
                {isLocationValid ? `${lat.toFixed(5)}, ${lng.toFixed(5)}` : 'Awaiting coordinates...'}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={requestLocation}
            className="text-[10px] bg-[#162235] hover:bg-[#1f2f49] text-sky-300 px-2 py-1 rounded border border-[#293d5c] transition font-mono"
            aria-label="Refresh GPS Location"
          >
            Refresh GPS
          </button>
        </div>

        {/* 1-Tap Gated SOS Button */}
        <div className="text-center py-1">
          <button
            onClick={handleInstantSOS}
            disabled={isSubmitting || !isLocationValid}
            className="w-36 h-36 mx-auto rounded bg-rose-700 hover:bg-rose-600 active:bg-rose-800 text-white font-bold border-2 border-rose-500/80 flex flex-col items-center justify-center space-y-1 transition active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
            aria-label="Send Instant SOS Beacon"
          >
            <AlertOctagon className="w-8 h-8" />
            <span className="text-base font-extrabold tracking-wide font-mono">SEND SOS</span>
            <span className="text-[9px] tracking-widest uppercase text-rose-200 font-mono">1-TAP ALERT</span>
          </button>
          <p className="text-[10px] text-slate-400 mt-2 font-mono">
            {isLocationValid
              ? 'Transmits high-priority GPS distress beacon to Sector 18 Dispatch'
              : '⚠️ GPS lock or manual landmark required before activating SOS'}
          </p>
        </div>

        {/* Submission Confirmation Alert */}
        {submittedEvent && (
          <div
            role="alert"
            className="bg-[#032e22] border border-emerald-700 p-3 rounded space-y-1.5 text-xs text-slate-200 font-mono select-text"
          >
            <div className="flex items-center justify-between text-emerald-300 font-bold">
              <span className="flex items-center">
                <CheckCircle2 className="w-4 h-4 mr-1 text-emerald-400" />
                {submittedEvent.status === 'QUEUED_OFFLINE' ? 'STORED IN OFFLINE OUTBOX' : 'DISTRESS BEACON TRANSMITTED'}
              </span>
              <span>#{submittedEvent.id}</span>
            </div>
            <div className="text-[11px] text-slate-300 font-sans">
              CAD Status: <strong className="text-white">{submittedEvent.status}</strong>
            </div>
            <div className="text-[11px] text-emerald-300 font-sans">
              Assigned: <strong>{submittedEvent.assigned_unit ? submittedEvent.assigned_unit.name : 'NDRF Quick Response Team'}</strong>
            </div>
            {submittedEvent.summary && (
              <div className="text-[11px] text-slate-400 mt-1">
                {submittedEvent.summary}
              </div>
            )}
          </div>
        )}

        {/* Structured Emergency Report Form */}
        <form onSubmit={handleSubmit} className="space-y-3.5 pt-2 border-t border-[#1b2537] text-xs">
          <div className="text-[11px] uppercase font-bold tracking-wider text-slate-400 font-mono">
            Or Submit Detailed Incident Report:
          </div>

          {/* Emergency Category */}
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">Emergency Category</label>
            <div className="grid grid-cols-3 gap-1.5 text-[11px] font-medium">
              {[
                { cat: 'FLOOD', icon: <Waves className="w-3.5 h-3.5 text-cyan-400" /> },
                { cat: 'FIRE', icon: <Flame className="w-3.5 h-3.5 text-orange-400" /> },
                { cat: 'RESCUE', icon: <LifeBuoy className="w-3.5 h-3.5 text-rose-400" /> },
                { cat: 'AMBULANCE', icon: <HeartPulse className="w-3.5 h-3.5 text-emerald-400" /> },
                { cat: 'POLICE', icon: <ShieldAlert className="w-3.5 h-3.5 text-blue-400" /> }
              ].map(({ cat, icon }) => (
                <button
                  type="button"
                  key={cat}
                  onClick={() => setCategory(cat)}
                  className={`p-2 rounded border flex items-center justify-center space-x-1.5 transition ${
                    category === cat
                      ? 'bg-[#182538] text-white border-blue-500 font-bold'
                      : 'bg-[#101726] border-[#223046] text-slate-400 hover:text-slate-200'
                  }`}
                  aria-pressed={category === cat}
                >
                  {icon}
                  <span>{cat}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Sector & Casualties */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[11px] text-slate-400 block mb-1">Landmark / Sector</label>
              <input
                type="text"
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                placeholder="e.g. Building 12, River Road"
                className="w-full p-2 bg-[#101726] border border-[#223046] rounded text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                aria-label="Incident Landmark or Sector"
              />
            </div>
            <div>
              <label className="text-[11px] text-slate-400 block mb-1">Casualties / Trapped</label>
              <input
                type="number"
                min="0"
                max="50"
                value={casualtyCount}
                onChange={(e) => setCasualtyCount(e.target.value)}
                className="w-full p-2 bg-[#101726] border border-[#223046] rounded text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
                aria-label="Casualties Count"
              />
            </div>
          </div>

          {/* GPS Coordinates Display & Manual Entry */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[11px] text-slate-400 block mb-1">Latitude</label>
              <input
                type="number"
                step="0.0001"
                min="-90"
                max="90"
                value={lat !== null ? lat : ''}
                onChange={(e) => setLat(parseFloat(e.target.value))}
                placeholder="28.6145"
                className="w-full p-2 bg-[#101726] border border-[#223046] rounded text-xs text-slate-200 font-mono focus:outline-none focus:border-blue-500"
                aria-label="Incident Latitude"
              />
            </div>
            <div>
              <label className="text-[11px] text-slate-400 block mb-1">Longitude</label>
              <input
                type="number"
                step="0.0001"
                min="-180"
                max="180"
                value={lng !== null ? lng : ''}
                onChange={(e) => setLng(parseFloat(e.target.value))}
                placeholder="77.2085"
                className="w-full p-2 bg-[#101726] border border-[#223046] rounded text-xs text-slate-200 font-mono focus:outline-none focus:border-blue-500"
                aria-label="Incident Longitude"
              />
            </div>
          </div>

          {/* Incident Description */}
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">Emergency Description</label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="State what is happening, immediate danger, injuries..."
              className="w-full p-2 bg-[#101726] border border-[#223046] rounded text-xs text-slate-200 focus:outline-none focus:border-blue-500 select-text"
              aria-label="Emergency Description"
            />
          </div>

          {/* Camera / Photo Upload */}
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">Attach Crisis Photo (Optional)</label>
            <div className="flex items-center space-x-2">
              <label className="flex-1 p-2 bg-[#101726] border border-[#223046] rounded text-center cursor-pointer hover:border-slate-500 transition text-slate-300 text-xs flex items-center justify-center space-x-1.5">
                <Camera className="w-4 h-4 text-slate-400" />
                <span className="truncate">{imageFile ? imageFile.name : 'Take Photo or Choose File'}</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setImageFile(e.target.files[0])}
                  className="hidden"
                />
              </label>
              {imageFile && (
                <button
                  type="button"
                  onClick={() => setImageFile(null)}
                  className="text-xs text-rose-400 hover:text-rose-300 p-2"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Submit Report Button */}
          <button
            type="submit"
            disabled={isSubmitting || !isLocationValid}
            className="w-full py-2.5 rounded bg-blue-700 hover:bg-blue-600 text-white font-bold text-xs flex items-center justify-center space-x-2 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Transmitting Report...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>Transmit Incident Report</span>
              </>
            )}
          </button>
        </form>

        {/* Official Emergency Numbers Footer */}
        <div className="pt-3 border-t border-[#1b2537] text-[10px] text-slate-400 text-center font-mono">
          <span>EMERGENCY HELPLINES: </span>
          <span className="text-slate-200">112 (NATIONAL) • 101 (FIRE) • 108 (EMS)</span>
        </div>
      </div>
    </div>
  );
}
