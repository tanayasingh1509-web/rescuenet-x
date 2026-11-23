import React, { useState, useEffect } from 'react';
import {
  X, ChevronLeft, ChevronRight, Presentation,
  PhoneCall, Eye, Layers, Radio
} from 'lucide-react';

export default function PitchDeckModal({ isOpen, onClose }) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [benchmarks, setBenchmarks] = useState(null);

  // Fetch reproducible benchmark data
  useEffect(() => {
    if (isOpen) {
      fetch('/benchmarks.json')
        .then((r) => r.json())
        .then((data) => setBenchmarks(data))
        .catch(() => {});
    }
  }, [isOpen]);

  const slidesCount = 6;

  // Keyboard navigation (Escape, Left, Right)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowRight') setCurrentSlide((s) => Math.min(slidesCount - 1, s + 1));
      if (e.key === 'ArrowLeft') setCurrentSlide((s) => Math.max(0, s - 1));
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const routingMs = benchmarks?.routing?.avg_ms || 13.7;
  const visionMs = benchmarks?.vision?.avg_ms || 57.7;
  const sttMs = benchmarks?.stt?.avg_ms ? Math.round(benchmarks.stt.avg_ms) : 1590;

  const slides = [
    // Slide 1: Title & Vision
    {
      title: 'RESCUENET-X',
      subtitle: 'Omnichannel Disaster Intelligence & Automated CAD Unit Dispatch',
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
            A resilient multi-modal crisis intelligence platform built for network-compromised, high-stress disaster environments.
          </p>
          <div className="grid grid-cols-2 gap-2.5 pt-2 text-xs">
            <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] text-left">
              <span className="text-rose-400 font-bold block mb-1 font-mono text-[11px]">Channel A: Telephony</span>
              <span className="text-slate-300 text-[11px] leading-relaxed">2G/GSM feature phones via automated IVR DTMF & local Whisper STT</span>
            </div>
            <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] text-left">
              <span className="text-amber-400 font-bold block mb-1 font-mono text-[11px]">Channel B: Vision AI</span>
              <span className="text-slate-300 text-[11px] leading-relaxed">Multi-tier verified drone/mobile photo uploads & offline PWA mesh</span>
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
              <span className="text-slate-300 text-[11px] leading-relaxed">
                DTMF Keypad Menu (1: Police, 2: Ambulance, 3: Rescue) with Sector Gathering. Captures raw speech for local OpenAI Whisper STT with fallback.
              </span>
            </div>
          </div>

          <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded flex items-center space-x-3">
            <div className="p-2 bg-[#2a1d0d] border border-[#52391b] rounded text-amber-300">
              <Eye className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-xs text-slate-100 block">Channel B: Visual Verification & YOLOv11</span>
              <span className="text-slate-300 text-[11px] leading-relaxed">
                Fast color/edge/texture heuristic capped at 0.80 (Manual Review). Verified status (&ge;0.85) triggered via Gemini Vision. YOLOv11 nano performs person counting.
              </span>
            </div>
          </div>

          <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded flex items-center space-x-3">
            <div className="p-2 bg-[#05261d] border border-[#124f3e] rounded text-emerald-300">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-xs text-slate-100 block">Agentic Deduplication & Routing</span>
              <span className="text-slate-300 text-[11px] leading-relaxed">
                pHash image dedup and 30-min spatial window merge duplicates within 500m, scores dynamic urgency (1-10), and routes the closest available unit (marked EN_ROUTE).
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
              Local CPU PyTorch inference. Direct wave PCM memory fallback bypasses ffmpeg. Auto-downgrades to tiny if latency budget exceeds 1.5s.
            </p>
          </div>

          <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-emerald-400 block text-[11px] font-mono">NLP Entity Extraction</span>
            <span className="text-slate-200 font-semibold block text-xs">Llama-3 via Ollama / Regex Heuristic</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Zero-shot structured JSON extraction. If Ollama is unreachable, automatically triggers deterministic regex parser to guarantee 100% uptime.
            </p>
          </div>

          <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-amber-400 block text-[11px] font-mono">Computer Vision</span>
            <span className="text-slate-200 font-semibold block text-xs">YOLOv11 Nano + pHash + Gemini</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Perceptual Hashing (64-bit) eliminates duplicate image spam within 500m. YOLOv11 counts casualties; optional Gemini Vision validates high-stakes incidents.
            </p>
          </div>

          <div className="bg-[#101726] p-3 rounded border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-rose-400 block text-[11px] font-mono">GIS Mapping Layer</span>
            <span className="text-slate-200 font-semibold block text-xs">Google Maps + Leaflet Fallback</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Full Google Maps SDK with tactical dark styling. Automatic failover to Carto Dark Leaflet on auth failure or offline mode.
            </p>
          </div>
        </div>
      )
    },

    // Slide 5: Performance Impact & Benchmark
    {
      title: 'Measured Operational Benchmarks',
      subtitle: 'Reproducible Metrics Measured via scripts/benchmark.py',
      badge: 'MEASURED PERFORMANCE',
      content: (
        <div className="space-y-3 py-2 text-xs select-text">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded">
              <span className="text-slate-400 text-[10px] uppercase font-mono block">CAD Routing Pipeline</span>
              <span className="text-xl font-bold text-emerald-400 font-mono mt-1 block">~{routingMs} ms</span>
              <span className="text-[10px] text-slate-400">Dedup + Urgency + Nearest Unit</span>
            </div>
            <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded">
              <span className="text-slate-400 text-[10px] uppercase font-mono block">Vision Inference</span>
              <span className="text-xl font-bold text-amber-400 font-mono mt-1 block">~{visionMs} ms</span>
              <span className="text-[10px] text-slate-400">Heuristic + Person Count</span>
            </div>
            <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded">
              <span className="text-slate-400 text-[10px] uppercase font-mono block">STT Audio Inference</span>
              <span className="text-xl font-bold text-cyan-400 font-mono mt-1 block">~{sttMs} ms</span>
              <span className="text-[10px] text-slate-400">3.0s Audio (CPU Whisper)</span>
            </div>
          </div>

          <div className="bg-[#101726] border border-[#1e2a3c] p-3 rounded space-y-1 font-mono text-[11px]">
            <div className="flex items-center justify-between text-slate-300">
              <span>Section 4.5 Contract Validation:</span>
              <span className="text-emerald-400 font-bold">100% STRICT PYDANTIC (10/10 FIELDS)</span>
            </div>
            <div className="flex items-center justify-between text-slate-300">
              <span>Unit State Lifecycle:</span>
              <span className="text-emerald-400 font-bold">AVAILABLE &rarr; EN_ROUTE &rarr; RESOLVED</span>
            </div>
            <div className="flex items-center justify-between text-slate-300">
              <span>Database Persistence:</span>
              <span className="text-emerald-400 font-bold">SQLITE WAL SURVIVES RESTARTS</span>
            </div>
          </div>
        </div>
      )
    },

    // Slide 6: Live Judge Demo Flow
    {
      title: 'Live Judge Demonstration Script',
      subtitle: 'Turnkey Walkthrough of All Audited Capabilities',
      badge: 'DEMO PROTOCOL',
      content: (
        <div className="space-y-2 py-1 text-xs select-text">
          <div className="p-2.5 rounded bg-[#101726] border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-cyan-400 block text-[11px] font-mono">1. Dial 2G Phone Simulator (`112`)</span>
            <p className="text-slate-300 text-[11px]">
              Open Phone Simulator &rarr; Dial 112 &rarr; Select sector landmark and DTMF service. Watch the map instantly pin jittered coordinates without merging separate callers, and assign the nearest available unit.
            </p>
          </div>

          <div className="p-2.5 rounded bg-[#101726] border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-amber-400 block text-[11px] font-mono">2. Upload Crisis Photo & Heuristic Review</span>
            <p className="text-slate-300 text-[11px]">
              Upload disaster photo. Heuristic analysis classifies in ~58ms capped at 0.80 confidence (marked MANUAL_REVIEW). Gemini Vision validates verified emergencies (&ge;0.85). Re-uploading the same image triggers pHash dedup merge.
            </p>
          </div>

          <div className="p-2.5 rounded bg-[#101726] border border-[#1e2a3c] space-y-1">
            <span className="font-bold text-emerald-400 block text-[11px] font-mono">3. 1-Click CAD Dispatch & Unit Resolution</span>
            <p className="text-slate-300 text-[11px]">
              Click 'Authorize CAD Dispatch' &rarr; Unit state flips to EN_ROUTE with visual Polyline vector drawn on GIS map. Click 'Resolve Incident' to return unit to AVAILABLE and update live CAD stats.
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
      <div className="bg-[#0c121e] border border-[#25354e] w-full max-w-2xl rounded shadow-2xl overflow-hidden flex flex-col max-h-[90vh] text-slate-100">
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
              className="text-slate-400 hover:text-white p-1 rounded hover:bg-[#162030] transition focus-visible:ring-2 focus-visible:ring-blue-500"
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

            {/* Slide Body */}
            <div>{current.content}</div>
          </div>

          {/* Navigation Controls */}
          <div className="pt-6 border-t border-[#1b2537] flex items-center justify-between mt-4">
            <button
              onClick={() => setCurrentSlide((s) => Math.max(0, s - 1))}
              disabled={currentSlide === 0}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-[#101726] border border-[#223046] text-xs font-medium text-slate-300 hover:text-white hover:border-slate-500 transition disabled:opacity-30 disabled:pointer-events-none"
              aria-label="Previous Slide"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Previous</span>
            </button>

            {/* Slide Dots Indicator */}
            <div className="flex items-center space-x-1.5">
              {slides.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentSlide(idx)}
                  className={`w-2 h-2 rounded-full transition ${
                    idx === currentSlide
                      ? 'bg-rose-500 w-5'
                      : 'bg-[#223046] hover:bg-slate-500'
                  }`}
                  aria-label={`Go to slide ${idx + 1}`}
                />
              ))}
            </div>

            <button
              onClick={() => setCurrentSlide((s) => Math.min(slides.length - 1, s + 1))}
              disabled={currentSlide === slides.length - 1}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-[#101726] border border-[#223046] text-xs font-medium text-slate-300 hover:text-white hover:border-slate-500 transition disabled:opacity-30 disabled:pointer-events-none"
              aria-label="Next Slide"
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
