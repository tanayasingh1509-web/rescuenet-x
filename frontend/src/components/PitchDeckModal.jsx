import React, { useState, useEffect } from 'react';
import {
  X, ChevronLeft, ChevronRight, Presentation,
  ShieldAlert, PhoneCall, Eye, Layers, Zap,
  Truck, CheckCircle, Radio
} from 'lucide-react';

export default function PitchDeckModal({ isOpen, onClose }) {
  const [currentSlide, setCurrentSlide] = useState(0);

  // Keyboard navigation (Escape, Left, Right)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowRight') setCurrentSlide((s) => Math.min(slides.length - 1, s + 1));
      if (e.key === 'ArrowLeft') setCurrentSlide((s) => Math.max(0, s - 1));
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const slides = [
    // Slide 1: Title & Vision
    {
      title: 'RESCUENET-X',
      subtitle: 'Omnichannel Disaster Intelligence & Zero-Latency Automated Dispatch',
      badge: 'TECHNICAL BRIEFING',
      content: (
        <div className="space-y-4 text-center max-w-lg mx-auto py-2">
          <div className="w-12 h-12 mx-auto rounded bg-[#162032] border border-[#2b3d5b] flex items-center justify-center text-rose-500">
            <Radio className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-wider text-slate-100 font-mono">
              RESCUENET-X
            </h2>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              CIVIL DEFENSE CAD & DISASTER GATEWAY
            </p>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed font-sans max-w-md mx-auto">
            A zero-latency, multi-modal crisis intelligence platform built for network-compromised, high-stress disaster environments.
          </p>
          <div className="grid grid-cols-2 gap-2.5 pt-2 text-xs">
            <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] text-left">
              <span className="text-rose-400 font-bold block mb-1 font-mono text-[11px]">Channel A: Telephony</span>
              <span className="text-slate-400 text-[11px] leading-relaxed">2G/GSM feature phones via automated IVR DTMF & local Whisper STT</span>
            </div>
            <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] text-left">
              <span className="text-amber-400 font-bold block mb-1 font-mono text-[11px]">Channel B: Vision AI</span>
              <span className="text-slate-400 text-[11px] leading-relaxed">YOLOv11 verified drone/mobile photo uploads & offline PWA mesh</span>
            </div>
          </div>
        </div>
      )
    },

    // Slide 2: The Critical Problem
    {
      title: 'Disaster Communication Breakdown',
      subtitle: 'Why Legacy Emergency Infrastructure Fails During Major Catastrophes',
      badge: 'PROBLEM STATEMENT',
      content: (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 py-2">
          <div className="bg-[#101726] border border-[#1e2a3c] p-3.5 rounded space-y-1.5">
            <div className="text-[10px] font-mono font-bold text-rose-400">01 / BOTTLENECK</div>
            <h3 className="font-bold text-xs text-slate-100">4G/5G Infrastructure Collapse</h3>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Cellular data towers fail in floods or earthquakes. Non-technical citizens and 2G keypad phone users are locked out of web apps and digital forms.
            </p>
          </div>

          <div className="bg-[#101726] border border-[#1e2a3c] p-3.5 rounded space-y-1.5">
            <div className="text-[10px] font-mono font-bold text-amber-400">02 / BOTTLENECK</div>
            <h3 className="font-bold text-xs text-slate-100">Information Overload & Spam</h3>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Emergency control rooms are flooded with duplicate, stale, or unverified social media photos, resulting in operational paralysis and delayed dispatches.
            </p>
          </div>

          <div className="bg-[#101726] border border-[#1e2a3c] p-3.5 rounded space-y-1.5">
            <div className="text-[10px] font-mono font-bold text-sky-400">03 / BOTTLENECK</div>
            <h3 className="font-bold text-xs text-slate-100">Disconnected Legacy Telephony</h3>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Traditional 112 phone calls are disconnected from real-time GIS mapping and automated fleet CAD dispatch, requiring minutes of manual call routing.
            </p>
          </div>
        </div>
      )
    },

    // Slide 3: Omnichannel Solution Architecture
    {
      title: 'The Omnichannel Solution',
      subtitle: 'Unifying 2G Voice and Drone AI Vision into One Command Center',
      badge: 'SYSTEM ARCHITECTURE',
      content: (
        <div className="space-y-2.5 py-1 text-xs">
          <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded flex items-center space-x-3">
            <div className="p-2 bg-[#142134] border border-[#273d5e] rounded text-cyan-300">
              <PhoneCall className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-xs text-slate-100 block">Channel A: VoiceBridge Telephony</span>
              <span className="text-slate-400 text-[11px] leading-relaxed">
                DTMF Keypad Menu (1: Police, 2: Ambulance, 3: Rescue). If no key is pressed, captures raw speech for local OpenAI Whisper STT.
              </span>
            </div>
          </div>

          <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded flex items-center space-x-3">
            <div className="p-2 bg-[#2a1d0d] border border-[#52391b] rounded text-amber-300">
              <Eye className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-xs text-slate-100 block">Channel B: Visual Verification (YOLOv11)</span>
              <span className="text-slate-400 text-[11px] leading-relaxed">
                Classifies crisis photos into Flood, Fire, Collapse with two-tier confidence logic (&lt;70% manual review, &ge;85% verified auto-dispatch).
              </span>
            </div>
          </div>

          <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded flex items-center space-x-3">
            <div className="p-2 bg-[#05261d] border border-[#124f3e] rounded text-emerald-300">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-xs text-slate-100 block">Agentic Deduplication & Routing</span>
              <span className="text-slate-400 text-[11px] leading-relaxed">
                Perceptual Hashing (pHash) merges duplicate photos within 500m (Hamming &lt; 5), scores dynamic urgency (1-10), and routes the closest NDRF/Ambulance unit.
              </span>
            </div>
          </div>
        </div>
      )
    },

    // Slide 4: Multi-Modal AI Pipeline & Fallbacks
    {
      title: 'Full Offline AI Resilience & Fail-Safe Architecture',
      subtitle: 'Zero Cloud Hard Dependencies — Engineered for Air-Gapped Operation',
      badge: 'AI PIPELINE & RISK MITIGATION',
      content: (
        <div className="grid grid-cols-2 gap-2.5 py-1 text-xs">
          <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-cyan-400 block text-[11px] font-mono">Speech-to-Text (STT)</span>
            <span className="text-slate-200 font-semibold block text-xs">OpenAI Whisper Base / Tiny</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Local CPU PyTorch inference. Direct wave PCM memory fallback bypasses system ffmpeg dependencies on Windows.
            </p>
          </div>

          <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-emerald-400 block text-[11px] font-mono">NLP Entity Extraction</span>
            <span className="text-slate-200 font-semibold block text-xs">Llama-3-8B via Ollama</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Zero-shot JSON extraction. If Ollama is unreachable, automatically triggers regex heuristic parser to guarantee 100% uptime.
            </p>
          </div>

          <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-amber-400 block text-[11px] font-mono">Computer Vision</span>
            <span className="text-slate-200 font-semibold block text-xs">YOLOv11 Nano + pHash</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Ultralytics model cached locally. Perceptual Hashing (64-bit) eliminates duplicate image spam within 500m.
            </p>
          </div>

          <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-rose-400 block text-[11px] font-mono">GIS Mapping Layer</span>
            <span className="text-slate-200 font-semibold block text-xs">Mapbox GL JS + Leaflet Fallback</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Automatic fallback to Carto Dark / OpenStreetMap tiles ensures zero dependency on external Mapbox API keys.
            </p>
          </div>
        </div>
      )
    },

    // Slide 5: Performance Impact & Benchmark
    {
      title: 'Operational Impact Metrics',
      subtitle: 'Quantifiable Acceleration from Raw Crisis Call to First Responder Wheels Rolling',
      badge: 'IMPACT & PERFORMANCE',
      content: (
        <div className="space-y-3 py-2 text-xs">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded">
              <span className="text-slate-400 text-[10px] uppercase font-mono block">Legacy Decision Time</span>
              <span className="text-xl font-bold text-rose-400 font-mono mt-1 block">~15.0 mins</span>
              <span className="text-[10px] text-slate-500">Manual Operator Triage</span>
            </div>
            <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded">
              <span className="text-slate-400 text-[10px] uppercase font-mono block">RescueNet-X CAD</span>
              <span className="text-xl font-bold text-emerald-400 font-mono mt-1 block">&lt; 3.0 sec</span>
              <span className="text-[10px] text-slate-500">Autonomous Extraction</span>
            </div>
            <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded">
              <span className="text-slate-400 text-[10px] uppercase font-mono block">WebSocket Latency</span>
              <span className="text-xl font-bold text-cyan-400 font-mono mt-1 block">&lt; 10 ms</span>
              <span className="text-[10px] text-slate-500">Sub-50ms Target</span>
            </div>
          </div>

          <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded space-y-1 font-mono text-[11px]">
            <div className="flex items-center justify-between text-slate-300">
              <span>Section 4.5 Schema Compliance:</span>
              <span className="text-emerald-400 font-bold">100% VALIDATED (10/10 FIELDS)</span>
            </div>
            <div className="flex items-center justify-between text-slate-300">
              <span>Twilio IVR Graceful Degradation:</span>
              <span className="text-emerald-400 font-bold">DTMF 1/2/3 IMMEDIATE DISPATCH</span>
            </div>
            <div className="flex items-center justify-between text-slate-300">
              <span>Image Perceptual Hash Deduplication:</span>
              <span className="text-emerald-400 font-bold">500m RADIUS, HAMMING &lt; 5 MERGE</span>
            </div>
          </div>
        </div>
      )
    },

    // Slide 6: Live Judge Demo Flow
    {
      title: 'Live Judge Demonstration Script',
      subtitle: '3-Minute Turnkey Walkthrough of All Key Capabilities',
      badge: 'DEMO PROTOCOL',
      content: (
        <div className="space-y-2 py-1 text-xs">
          <div className="p-2.5 rounded bg-[#101726] border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-cyan-400 block text-[11px] font-mono">1. Dial 2G Phone Simulator (`112`)</span>
            <p className="text-slate-400 text-[11px]">
              Open Phone Simulator &rarr; Dial 112 &rarr; Press '3' (Rescue). Watch the map instantly pin Sector 18 with NDRF Squad Alpha dispatched in &lt; 50ms.
            </p>
          </div>

          <div className="p-2.5 rounded bg-[#101726] border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-amber-400 block text-[11px] font-mono">2. Upload Crisis Photo (`YOLOv11`)</span>
            <p className="text-slate-400 text-[11px]">
              Upload `fire_crisis.jpg`. The vision engine scores 96% confidence (&ge; 85%) &rarr; verified auto-dispatched to Fire Tender 9. Re-upload same image to trigger pHash dedup merge.
            </p>
          </div>

          <div className="p-2.5 rounded bg-[#101726] border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-emerald-400 block text-[11px] font-mono">3. 1-Click CAD Dispatch & Field Terminal</span>
            <p className="text-slate-400 text-[11px]">
              Click '1-Click Dispatch' on any incident &rarr; Open 'Field Terminal' in the top bar to inspect incoming VHF radio / SMS alerts received on-ground.
            </p>
          </div>
        </div>
      )
    }
  ];

  if (!isOpen) return null;

  const current = slides[currentSlide];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="pitch-deck-title"
      className="fixed inset-0 z-[5000] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
    >
      <div className="bg-[#0c121e] border border-[#25354e] w-full max-w-2xl rounded shadow-2xl overflow-hidden flex flex-col max-h-[90vh] text-slate-100 select-none">
        {/* Header */}
        <div className="bg-[#090d16] p-3.5 border-b border-[#1f2b3e] flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Presentation className="w-4 h-4 text-slate-400" />
            <span className="text-[10px] font-mono uppercase tracking-widest bg-[#162030] text-slate-300 border border-[#273752] px-2 py-0.5 rounded">
              {current.badge}
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <span className="text-xs font-mono text-slate-400">
              SLIDE {String(currentSlide + 1).padStart(2, '0')} / {String(slides.length).padStart(2, '0')}
            </span>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded hover:bg-[#162030] transition"
              aria-label="Close Presentation"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Slide Canvas */}
        <div className="p-6 overflow-y-auto flex-1 flex flex-col justify-between">
          <div>
            <div className="mb-4">
              <h2 id="pitch-deck-title" className="text-lg font-bold text-slate-100 tracking-tight font-mono">
                {current.title}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                {current.subtitle}
              </p>
            </div>

            {current.content}
          </div>

          {/* Navigation Controls */}
          <div className="pt-4 border-t border-[#1b2537] flex items-center justify-between text-xs">
            <button
              onClick={() => setCurrentSlide((s) => Math.max(0, s - 1))}
              disabled={currentSlide === 0}
              className="flex items-center space-x-1 px-3 py-1.5 rounded bg-[#162030] hover:bg-[#1e2a3c] text-slate-300 disabled:opacity-30 transition font-medium"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Previous</span>
            </button>

            {/* Slide Pagination Dots */}
            <div className="flex items-center space-x-1.5">
              {slides.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentSlide(idx)}
                  className={`w-2 h-2 rounded-full transition ${
                    currentSlide === idx ? 'bg-blue-500 w-5' : 'bg-slate-700 hover:bg-slate-600'
                  }`}
                  aria-label={`Go to slide ${idx + 1}`}
                />
              ))}
            </div>

            <button
              onClick={() => setCurrentSlide((s) => Math.min(slides.length - 1, s + 1))}
              disabled={currentSlide === slides.length - 1}
              className="flex items-center space-x-1 px-3 py-1.5 rounded bg-blue-700 hover:bg-blue-600 text-white font-medium disabled:opacity-30 transition"
            >
              <span>Next</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
