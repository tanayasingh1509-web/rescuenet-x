import React, { useState } from 'react';
import {
  AlertOctagon, Waves, Flame, HeartPulse, ShieldAlert,
  LifeBuoy, MapPin, Camera, Send, CheckCircle2,
  Clock, PhoneCall, Radio, ArrowLeft, Loader2, Navigation, Shield
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || '';

export default function CitizenPortal({ onBackToCommand }) {
  const [category, setCategory] = useState('FLOOD');
  const [sector, setSector] = useState('Citizen Hotspot Node B');
  const [description, setDescription] = useState('');
  const [casualtyCount, setCasualtyCount] = useState(1);
  const [lat, setLat] = useState(28.6145);
  const [lng, setLng] = useState(77.2085);
  const [imageFile, setImageFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedEvent, setSubmittedEvent] = useState(null);

  // Auto-fetch GPS if available
  const handleGetLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLat(pos.coords.latitude);
          setLng(pos.coords.longitude);
        },
        (err) => console.log('Geolocation unavailable:', err)
      );
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
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
          body: JSON.stringify({
            category,
            lat,
            lng,
            sector,
            casualty_count: parseInt(casualtyCount, 10),
            severity: 8,
            description: description || `Citizen reported ${category} emergency.`
          })
        });
        const data = await res.json();
        setSubmittedEvent(data.event);
      }
    } catch (err) {
      console.error('Citizen submission error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInstantSOS = async () => {
    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/report/pwa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: 'RESCUE',
          lat,
          lng,
          sector: 'CRITICAL INSTANT SOS BEACON',
          casualty_count: 1,
          severity: 10,
          description: 'INSTANT SOS BEACON ACTIVATED! Immediate search & rescue response required.'
        })
      });
      const data = await res.json();
      setSubmittedEvent(data.event);
    } catch (err) {
      console.error('SOS failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e17] text-slate-100 flex flex-col items-center p-3 sm:p-5 select-none font-sans">
      {/* Top Banner */}
      <div className="w-full max-w-lg flex items-center justify-between py-2 border-b border-[#1b2537] mb-4">
        <button
          onClick={onBackToCommand}
          className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-white transition font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to CAD Command</span>
        </button>
        <span className="text-[10px] font-mono bg-[#0f231d] text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded flex items-center">
          <Radio className="w-3 h-3 mr-1 text-emerald-400" />
          OFFLINE PWA MESH READY
        </span>
      </div>

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

        {/* 1-Tap SOS Button */}
        <div className="text-center py-1">
          <button
            onClick={handleInstantSOS}
            disabled={isSubmitting}
            className="w-36 h-36 mx-auto rounded bg-rose-700 hover:bg-rose-600 active:bg-rose-800 text-white font-bold border-2 border-rose-500/80 flex flex-col items-center justify-center space-y-1 transition active:scale-95 disabled:opacity-50 shadow-md"
          >
            <AlertOctagon className="w-8 h-8" />
            <span className="text-base font-extrabold tracking-wide font-mono">SEND SOS</span>
            <span className="text-[9px] tracking-widest uppercase text-rose-200 font-mono">1-TAP ALERT</span>
          </button>
          <p className="text-[10px] text-slate-500 mt-2 font-mono">
            Transmits high-priority GPS distress beacon to Sector 18 Dispatch
          </p>
        </div>

        {/* Submission Confirmation Alert */}
        {submittedEvent && (
          <div className="bg-[#032e22] border border-emerald-700 p-3 rounded space-y-1.5 text-xs text-slate-200 font-mono animate-fade-in">
            <div className="flex items-center justify-between text-emerald-300 font-bold">
              <span className="flex items-center">
                <CheckCircle2 className="w-4 h-4 mr-1 text-emerald-400" />
                DISTRESS BEACON TRANSMITTED
              </span>
              <span>#{submittedEvent.id}</span>
            </div>
            <div className="text-[11px] text-slate-300 font-sans">
              CAD Status: <strong className="text-white">{submittedEvent.status}</strong>
            </div>
            <div className="text-[11px] text-emerald-300 font-sans">
              Assigned: <strong>{submittedEvent.assigned_unit ? submittedEvent.assigned_unit.name : 'NDRF Quick Response Team'}</strong>
            </div>
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
                >
                  {icon}
                  <span>{cat}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Sector & GPS Location */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[11px] text-slate-400 block mb-1">Landmark / Sector</label>
              <input
                type="text"
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                placeholder="e.g. Building 12, River Road"
                className="w-full p-2 bg-[#101726] border border-[#223046] rounded text-xs text-slate-200 focus:outline-none focus:border-blue-500"
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
              />
            </div>
          </div>

          {/* GPS Coordinates Button */}
          <div className="flex items-center justify-between bg-[#101726] p-2 rounded border border-[#223046]">
            <div className="text-[11px] text-slate-300 font-mono flex items-center space-x-1.5">
              <MapPin className="w-3.5 h-3.5 text-slate-400" />
              <span>GPS: {lat.toFixed(4)}, {lng.toFixed(4)}</span>
            </div>
            <button
              type="button"
              onClick={handleGetLocation}
              className="text-[10px] bg-[#162235] hover:bg-[#1f2f49] text-sky-300 px-2 py-1 rounded border border-[#293d5c] transition font-mono"
            >
              Grab Device GPS
            </button>
          </div>

          {/* Incident Description */}
          <div>
            <label className="text-[11px] text-slate-400 block mb-1">Emergency Description</label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="State what is happening, immediate danger, injuries..."
              className="w-full p-2 bg-[#101726] border border-[#223046] rounded text-xs text-slate-200 focus:outline-none focus:border-blue-500"
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
            disabled={isSubmitting}
            className="w-full py-2.5 rounded bg-blue-700 hover:bg-blue-600 text-white font-bold text-xs flex items-center justify-center space-x-2 transition disabled:opacity-50"
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
        <div className="pt-3 border-t border-[#1b2537] text-[10px] text-slate-500 text-center font-mono">
          <span>EMERGENCY HELPLINES: </span>
          <span className="text-slate-300">112 (NATIONAL) • 101 (FIRE) • 108 (EMS)</span>
        </div>
      </div>
    </div>
  );
}
