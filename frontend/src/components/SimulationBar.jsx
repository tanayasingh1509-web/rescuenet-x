import React, { useState } from 'react';
import {
  Waves, HeartPulse, Flame, PhoneCall,
  Camera, RotateCcw, Play, Upload, Check, Loader2, X, Terminal
} from 'lucide-react';

export default function SimulationBar({
  onTriggerScenario,
  onSimulateVoice,
  onUploadImage,
  onReset
}) {
  const [loadingAction, setLoadingAction] = useState('');
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const [voiceText, setVoiceText] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleScenarioClick = async (name) => {
    setLoadingAction(name);
    try {
      await onTriggerScenario(name);
    } finally {
      setLoadingAction('');
    }
  };

  const handleVoiceSubmit = async (e) => {
    e.preventDefault();
    if (!voiceText.trim()) return;
    setLoadingAction('voice_sim');
    try {
      await onSimulateVoice(voiceText);
      setVoiceText('');
      setShowVoiceModal(false);
    } finally {
      setLoadingAction('');
    }
  };

  const handleImageSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;
    setLoadingAction('image_sim');
    try {
      await onUploadImage(selectedFile);
      setSelectedFile(null);
      setShowUploadModal(false);
    } finally {
      setLoadingAction('');
    }
  };

  return (
    <div className="bg-[#0b101a] border-t border-[#1b2537] px-4 py-2 flex items-center justify-between gap-3 text-xs overflow-x-auto select-none">
      {/* Module Title */}
      <div className="flex items-center space-x-2 shrink-0">
        <Terminal className="w-3.5 h-3.5 text-slate-400" />
        <span className="font-mono font-bold text-slate-300 uppercase tracking-wider text-[10px]">
          Scenario Injector:
        </span>
      </div>

      {/* 3 Pre-set Tactical Scenarios */}
      <div className="flex items-center space-x-2 shrink-0">
        <button
          onClick={() => handleScenarioClick('flood')}
          disabled={!!loadingAction}
          className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded bg-[#131b29] hover:bg-[#1b263b] border border-[#233148] text-slate-200 hover:text-white transition font-medium disabled:opacity-50"
        >
          {loadingAction === 'flood' ? <Loader2 className="w-3 h-3 animate-spin text-cyan-400" /> : <Waves className="w-3 h-3 text-cyan-400" />}
          <span>1. Flood (4 Trapped)</span>
        </button>

        <button
          onClick={() => handleScenarioClick('medical')}
          disabled={!!loadingAction}
          className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded bg-[#131b29] hover:bg-[#1b263b] border border-[#233148] text-slate-200 hover:text-white transition font-medium disabled:opacity-50"
        >
          {loadingAction === 'medical' ? <Loader2 className="w-3 h-3 animate-spin text-emerald-400" /> : <HeartPulse className="w-3 h-3 text-emerald-400" />}
          <span>2. Cardiac EMS</span>
        </button>

        <button
          onClick={() => handleScenarioClick('fire')}
          disabled={!!loadingAction}
          className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded bg-[#131b29] hover:bg-[#1b263b] border border-[#233148] text-slate-200 hover:text-white transition font-medium disabled:opacity-50"
        >
          {loadingAction === 'fire' ? <Loader2 className="w-3 h-3 animate-spin text-orange-400" /> : <Flame className="w-3 h-3 text-orange-400" />}
          <span>3. Hazmat Fire</span>
        </button>
      </div>

      {/* Custom Field Testing: Voice & Photo */}
      <div className="flex items-center space-x-2 shrink-0">
        <button
          onClick={() => setShowVoiceModal(true)}
          className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded bg-[#131b29] hover:bg-[#1b263b] border border-[#233148] text-slate-300 hover:text-white font-medium transition"
        >
          <PhoneCall className="w-3 h-3 text-slate-400" />
          <span>Simulate Audio</span>
        </button>

        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded bg-[#131b29] hover:bg-[#1b263b] border border-[#233148] text-slate-300 hover:text-white font-medium transition"
        >
          <Camera className="w-3 h-3 text-slate-400" />
          <span>Upload Image</span>
        </button>

        <button
          onClick={onReset}
          className="flex items-center space-x-1 px-2.5 py-1.5 rounded bg-[#131b29] hover:bg-[#1b263b] border border-[#233148] text-slate-400 hover:text-rose-300 transition"
          title="Reset Queue to Baseline"
        >
          <RotateCcw className="w-3 h-3" />
          <span>Reset CAD</span>
        </button>
      </div>

      {/* Voice Simulation Modal */}
      {showVoiceModal && (
        <div className="fixed inset-0 z-[3000] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-[#0c121e] border border-[#25354e] w-full max-w-md rounded p-5 text-slate-100 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e2a3c] mb-3">
              <span className="font-bold text-sm flex items-center space-x-2">
                <PhoneCall className="w-4 h-4 text-cyan-400" />
                <span>Simulate Emergency Voice Transmission</span>
              </span>
              <button
                onClick={() => setShowVoiceModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded hover:bg-[#162030]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleVoiceSubmit} className="space-y-3">
              <div>
                <label className="text-[11px] text-slate-400 block mb-1 font-semibold">
                  Distress Speech Transcript (processed through Whisper / NLP):
                </label>
                <textarea
                  rows={3}
                  value={voiceText}
                  onChange={(e) => setVoiceText(e.target.value)}
                  placeholder="e.g. Critical emergency! River barrier collapsed near Sector 18, 4 people trapped on building roof..."
                  className="w-full p-2.5 bg-[#101726] border border-[#233148] rounded text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-1">
                <button
                  type="button"
                  onClick={() => setShowVoiceModal(false)}
                  className="px-3 py-1.5 rounded bg-[#162030] hover:bg-[#1c293e] text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loadingAction === 'voice_sim' || !voiceText.trim()}
                  className="px-3.5 py-1.5 rounded bg-cyan-700 hover:bg-cyan-600 text-white font-bold transition flex items-center space-x-1.5 disabled:opacity-50"
                >
                  {loadingAction === 'voice_sim' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                  <span>Inject Voice Report</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Image Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-[3000] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-[#0c121e] border border-[#25354e] w-full max-w-md rounded p-5 text-slate-100 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e2a3c] mb-3">
              <span className="font-bold text-sm flex items-center space-x-2">
                <Camera className="w-4 h-4 text-amber-400" />
                <span>Upload Drone / Recon Crisis Photo</span>
              </span>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded hover:bg-[#162030]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleImageSubmit} className="space-y-3">
              <div className="border-2 border-dashed border-[#233148] rounded p-6 text-center hover:border-amber-500 transition cursor-pointer bg-[#101726]">
                <input
                  type="file"
                  accept="image/*"
                  id="image-file-input"
                  onChange={(e) => setSelectedFile(e.target.files[0])}
                  className="hidden"
                />
                <label htmlFor="image-file-input" className="cursor-pointer space-y-2 block">
                  <Upload className="w-8 h-8 mx-auto text-amber-400" />
                  <div className="text-xs text-slate-300 font-semibold">
                    {selectedFile ? selectedFile.name : 'Click to select crisis photo'}
                  </div>
                  <div className="text-[10px] text-slate-500">
                    Supports JPG, PNG (YOLOv11 verification & 64-bit pHash deduplication)
                  </div>
                </label>
              </div>

              <div className="flex justify-end space-x-2 pt-1">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-3 py-1.5 rounded bg-[#162030] hover:bg-[#1c293e] text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loadingAction === 'image_sim' || !selectedFile}
                  className="px-3.5 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-white font-bold transition flex items-center space-x-1.5 disabled:opacity-50"
                >
                  {loadingAction === 'image_sim' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                  <span>Verify with YOLO</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
