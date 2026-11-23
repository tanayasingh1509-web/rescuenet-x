import React, { useState, useEffect } from 'react';
import {
  X, Key, CheckCircle2, Eye, EyeOff,
  ExternalLink, Loader2, Save, ShieldCheck
} from 'lucide-react';
import { authFetch } from '../utils/auth';

const API_BASE = import.meta.env.VITE_API_BASE || '';

export default function ApiKeyModal({ isOpen, onClose }) {
  const [geminiKey, setGeminiKey] = useState('');
  const [googleMapsKey, setGoogleMapsKey] = useState('');
  const [mapboxToken, setMapboxToken] = useState('');
  const [twilioSid, setTwilioSid] = useState('');
  const [twilioToken, setTwilioToken] = useState('');
  const [twilioPhone, setTwilioPhone] = useState('');

  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [showGoogleMapsKey, setShowGoogleMapsKey] = useState(false);
  const [showMapboxToken, setShowMapboxToken] = useState(false);
  const [showTwilioToken, setShowTwilioToken] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [isTestingGemini, setIsTestingGemini] = useState(false);
  const [geminiTestStatus, setGeminiTestStatus] = useState(null); // { status: 'success' | 'error', message: '' }
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [maskedStatuses, setMaskedStatuses] = useState(null);

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

  // Load active key statuses from backend
  useEffect(() => {
    if (isOpen) {
      setSaveSuccess(false);
      setGeminiTestStatus(null);
      authFetch(`${API_BASE}/api/config/keys`)
        .then((r) => r.json())
        .then((data) => {
          setMaskedStatuses(data);
          if (data.gemini?.masked) setGeminiKey(data.gemini.masked);
          if (data.google_maps?.masked) setGoogleMapsKey(data.google_maps.masked);
          if (data.mapbox?.masked) setMapboxToken(data.mapbox.masked);
          if (data.twilio?.masked_sid) setTwilioSid(data.twilio.masked_sid);
          if (data.twilio?.phone_number) setTwilioPhone(data.twilio.phone_number);
        })
        .catch((err) => console.warn('Could not load key status:', err));
    }
  }, [isOpen]);

  const handleTestGemini = async () => {
    setIsTestingGemini(true);
    setGeminiTestStatus(null);
    try {
      const res = await authFetch(`${API_BASE}/api/config/test-gemini`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: geminiKey.includes('••') ? undefined : geminiKey })
      });
      const data = await res.json();
      if (data.status === 'connected') {
        setGeminiTestStatus({ status: 'success', message: `Connected: Google Gemini API (${data.model}) operational.` });
      } else {
        setGeminiTestStatus({ status: 'error', message: data.detail || 'Authentication failed. Please verify API key.' });
      }
    } catch {
      setGeminiTestStatus({ status: 'error', message: 'Test failed: Backend unreachable.' });
    } finally {
      setIsTestingGemini(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setSaveSuccess(false);

    const payload = {};
    if (geminiKey && !geminiKey.includes('••')) payload.gemini_api_key = geminiKey;
    if (googleMapsKey && !googleMapsKey.includes('••')) payload.google_maps_api_key = googleMapsKey;
    if (mapboxToken && !mapboxToken.includes('••')) payload.mapbox_token = mapboxToken;
    if (twilioSid && !twilioSid.includes('••')) payload.twilio_account_sid = twilioSid;
    if (twilioToken && !twilioToken.includes('••')) payload.twilio_auth_token = twilioToken;
    if (twilioPhone) payload.twilio_phone_number = twilioPhone;

    try {
      const res = await authFetch(`${API_BASE}/api/config/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.status === 'success') {
        setSaveSuccess(true);
      }
    } catch (err) {
      console.error('Failed to save API keys:', err);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="api-key-modal-title"
      className="fixed inset-0 z-[5000] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
    >
      <div className="bg-[#0c121e] border border-[#25354e] w-full max-w-xl rounded shadow-2xl overflow-hidden flex flex-col max-h-[90vh] text-slate-100">
        {/* Header */}
        <div className="bg-[#090d16] p-3.5 border-b border-[#1f2b3e] flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded bg-[#131c2c] border border-[#263752] flex items-center justify-center text-blue-400">
              <Key className="w-3.5 h-3.5" />
            </div>
            <div>
              <h2 id="api-key-modal-title" className="text-xs font-bold text-slate-100 flex items-center space-x-2 font-mono">
                <span>API CREDENTIALS & INTEGRATIONS</span>
                <span className="text-[10px] bg-[#162030] text-slate-300 border border-[#273752] px-1.5 py-0.2 rounded">
                  CONFIG
                </span>
              </h2>
              <p className="text-[11px] text-slate-400">
                Configure live API keys for Google Gemini, Mapbox GL JS, and Twilio Telephony
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-[#162030] transition focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Close API Key Configuration"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="p-4 overflow-y-auto space-y-4 text-xs">
          {/* Success Banner */}
          {saveSuccess && (
            <div role="alert" className="bg-[#032e22] border border-emerald-700 p-2.5 rounded flex items-center space-x-2 text-emerald-300 font-mono text-[11px] animate-fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>API credentials safely saved to environment (.env) and active runtime.</span>
            </div>
          )}

          {/* 1. Google Gemini API Key */}
          <div className="bg-[#101726] border border-[#1e2a3c] rounded p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5">
                <span className="font-bold text-xs text-slate-100 font-mono">1. Google Gemini API Key</span>
                <span className="text-[9px] font-mono bg-blue-950 text-blue-300 border border-blue-800 px-1 rounded">
                  LLM TRIAGE
                </span>
              </div>
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noreferrer"
                className="text-[10px] text-sky-400 hover:text-sky-300 flex items-center space-x-1 font-mono"
              >
                <span>Get Gemini Key</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              Enables high-accuracy cloud crisis intelligence parsing using Gemini models. If left empty, the engine uses local Ollama or offline heuristic parsing.
            </p>

            <div className="flex items-center space-x-1.5">
              <div className="relative flex-1">
                <input
                  type={showGeminiKey ? 'text' : 'password'}
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  placeholder="Enter Gemini API key..."
                  className="w-full pl-2.5 pr-8 py-1.5 bg-[#090d16] border border-[#233148] rounded text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500 font-mono"
                  aria-label="Google Gemini API Key"
                />
                <button
                  type="button"
                  onClick={() => setShowGeminiKey(!showGeminiKey)}
                  className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-300"
                  aria-label="Toggle Gemini API Key Visibility"
                >
                  {showGeminiKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>

              <button
                type="button"
                onClick={handleTestGemini}
                disabled={isTestingGemini || (!geminiKey && !maskedStatuses?.gemini?.configured)}
                className="px-2.5 py-1.5 rounded bg-[#162235] hover:bg-[#1f2f49] border border-[#2a3d5c] text-sky-300 font-medium text-[11px] transition flex items-center space-x-1 disabled:opacity-40"
                aria-label="Test Google Gemini API Key"
              >
                {isTestingGemini ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
                <span>Test Key</span>
              </button>
            </div>

            {geminiTestStatus && (
              <div role="alert" className={`p-2 rounded font-mono text-[10px] ${
                geminiTestStatus.status === 'success'
                  ? 'bg-[#032e22] text-emerald-300 border border-emerald-800'
                  : 'bg-[#38090f] text-rose-300 border border-rose-800'
              }`}>
                {geminiTestStatus.message}
              </div>
            )}
          </div>

          {/* 2. Google Maps API Key */}
          <div className="bg-[#101726] border border-[#1e2a3c] rounded p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5">
                <span className="font-bold text-xs text-slate-100 font-mono">2. Google Maps API Key</span>
                <span className="text-[9px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800 px-1 rounded">
                  ACTIVE GIS
                </span>
              </div>
              <a
                href="https://console.cloud.google.com/google/maps-apis/credentials"
                target="_blank"
                rel="noreferrer"
                className="text-[10px] text-sky-400 hover:text-sky-300 flex items-center space-x-1 font-mono"
              >
                <span>Google Cloud Console</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              Powers Google Maps Tactical Dark vector and Satellite projections for CAD emergency dispatch.
            </p>

            <div className="relative">
              <input
                type={showGoogleMapsKey ? 'text' : 'password'}
                value={googleMapsKey}
                onChange={(e) => setGoogleMapsKey(e.target.value)}
                placeholder="Enter Google Maps API key..."
                className="w-full pl-2.5 pr-8 py-1.5 bg-[#090d16] border border-[#233148] rounded text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500 font-mono"
                aria-label="Google Maps API Key"
              />
              <button
                type="button"
                onClick={() => setShowGoogleMapsKey(!showGoogleMapsKey)}
                className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-300"
                aria-label="Toggle Google Maps API Key Visibility"
              >
                {showGoogleMapsKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* 3. Mapbox Public Access Token */}
          <div className="bg-[#101726] border border-[#1e2a3c] rounded p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5">
                <span className="font-bold text-xs text-slate-100 font-mono">3. Mapbox Public Token</span>
                <span className="text-[9px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800 px-1 rounded">
                  GIS VECTOR
                </span>
              </div>
              <a
                href="https://account.mapbox.com/access-tokens/"
                target="_blank"
                rel="noreferrer"
                className="text-[10px] text-sky-400 hover:text-sky-300 flex items-center space-x-1 font-mono"
              >
                <span>Get Token</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              Enables Mapbox dark vector mapping. If left empty, the platform automatically runs on local Carto Dark / OpenStreetMap tiles.
            </p>

            <div className="relative">
              <input
                type={showMapboxToken ? 'text' : 'password'}
                value={mapboxToken}
                onChange={(e) => setMapboxToken(e.target.value)}
                placeholder="Enter Mapbox public token..."
                className="w-full pl-2.5 pr-8 py-1.5 bg-[#090d16] border border-[#233148] rounded text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500 font-mono"
                aria-label="Mapbox Public Token"
              />
              <button
                type="button"
                onClick={() => setShowMapboxToken(!showMapboxToken)}
                className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-300"
                aria-label="Toggle Mapbox Token Visibility"
              >
                {showMapboxToken ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* 4. Twilio Telephony Credentials */}
          <div className="bg-[#101726] border border-[#1e2a3c] rounded p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5">
                <span className="font-bold text-xs text-slate-100 font-mono">4. Twilio Telephony</span>
                <span className="text-[9px] font-mono bg-purple-950 text-purple-300 border border-purple-800 px-1 rounded">
                  2G VOICE / SMS
                </span>
              </div>
              <a
                href="https://console.twilio.com/"
                target="_blank"
                rel="noreferrer"
                className="text-[10px] text-sky-400 hover:text-sky-300 flex items-center space-x-1 font-mono"
              >
                <span>Twilio Console</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              Configures live phone numbers and webhooks via Ngrok. If testing offline, the integrated 2G Phone Simulator handles all IVR and DTMF calls locally.
            </p>

            <div className="space-y-1.5">
              <div>
                <label className="text-[10px] text-slate-400 font-mono block">TWILIO_ACCOUNT_SID</label>
                <input
                  type="text"
                  value={twilioSid}
                  onChange={(e) => setTwilioSid(e.target.value)}
                  placeholder="AC..."
                  className="w-full px-2.5 py-1.5 bg-[#090d16] border border-[#233148] rounded text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500 font-mono"
                  aria-label="Twilio Account SID"
                />
              </div>

              <div>
                <label className="text-[10px] text-slate-400 font-mono block">TWILIO_AUTH_TOKEN</label>
                <div className="relative">
                  <input
                    type={showTwilioToken ? 'text' : 'password'}
                    value={twilioToken}
                    onChange={(e) => setTwilioToken(e.target.value)}
                    placeholder="Enter auth token..."
                    className="w-full pl-2.5 pr-8 py-1.5 bg-[#090d16] border border-[#233148] rounded text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500 font-mono"
                    aria-label="Twilio Auth Token"
                  />
                  <button
                    type="button"
                    onClick={() => setShowTwilioToken(!showTwilioToken)}
                    className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-300"
                    aria-label="Toggle Twilio Auth Token Visibility"
                  >
                    {showTwilioToken ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="text-[10px] text-slate-400 font-mono block">TWILIO_PHONE_NUMBER</label>
                <input
                  type="text"
                  value={twilioPhone}
                  onChange={(e) => setTwilioPhone(e.target.value)}
                  placeholder="+1..."
                  className="w-full px-2.5 py-1.5 bg-[#090d16] border border-[#233148] rounded text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500 font-mono"
                  aria-label="Twilio Phone Number"
                />
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-2 border-t border-[#1b2537]">
            <span className="text-[10px] text-slate-400 font-mono">
              Saved directly to local .env configuration
            </span>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 rounded bg-[#162030] hover:bg-[#1e2a3c] text-slate-300 font-medium text-xs transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="px-4 py-1.5 rounded bg-blue-700 hover:bg-blue-600 text-white font-bold text-xs flex items-center space-x-1.5 transition disabled:opacity-50"
              >
                {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                <span>Save Credentials</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
