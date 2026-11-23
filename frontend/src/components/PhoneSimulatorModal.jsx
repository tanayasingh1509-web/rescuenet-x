import React, { useState, useEffect } from 'react';
import {
  Phone, PhoneCall, PhoneOff, Mic,
  Volume2, X, Radio, Terminal
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || '';

export default function PhoneSimulatorModal({ isOpen, onClose }) {
  const [callState, setCallState] = useState('IDLE'); // 'IDLE' | 'CALLING' | 'CONNECTED' | 'RECORDING' | 'ENDED'
  const [screenMessage, setScreenMessage] = useState('LINE READY: DIAL 112');
  const [ivrPrompt, setIvrPrompt] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [selectedDigit, setSelectedDigit] = useState(null);
  const [voiceText, setVoiceText] = useState('Emergency! Water is rising rapidly in Sector 18, 4 people trapped on roof!');
  const [statusLog, setStatusLog] = useState([]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        window.speechSynthesis.cancel();
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Voice synthesis helper to speak IVR prompts
  const speakText = (text, onEndCallback) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => {
        setIsSpeaking(false);
        if (onEndCallback) onEndCallback();
      };
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleStartCall = async () => {
    setCallState('CALLING');
    setScreenMessage('DIALING 112 EMERGENCY GATEWAY...');
    setSelectedDigit(null);

    try {
      const res = await fetch(`${API_BASE}/api/voice/incoming`, { method: 'POST' });
      const xmlText = await res.text();

      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
      const sayNodes = xmlDoc.getElementsByTagName('Say');
      let promptText = 'Welcome to RescueNet X Emergency Response. Press 1 for Police. Press 2 for Ambulance. Press 3 for Trapped Search and Rescue. Or stay on the line to speak your emergency report after the tone.';
      if (sayNodes.length > 0) {
        promptText = sayNodes[0].textContent;
      }

      setCallState('CONNECTED');
      setScreenMessage('IVR ACTIVE: PRESS 1, 2, OR 3');
      setIvrPrompt(promptText);
      setStatusLog((prev) => [...prev, `[${new Date().toLocaleTimeString()}] TwiML Gather IVR Session Initialized`]);

      speakText(promptText);
    } catch (err) {
      console.error('Call init failed:', err);
      setScreenMessage('CALL FAILED: SERVER UNREACHABLE');
      setCallState('IDLE');
    }
  };

  const handleKeypadPress = async (digit) => {
    if (callState !== 'CONNECTED') return;

    setSelectedDigit(digit);
    window.speechSynthesis.cancel();

    const catMap = {
      '1': 'POLICE EMERGENCY',
      '2': 'AMBULANCE & MEDICAL',
      '3': 'SEARCH & RESCUE'
    };
    const choiceDesc = catMap[digit] || 'CRISIS RESCUE';

    setScreenMessage(`DTMF [${digit}]: ${choiceDesc}`);
    setStatusLog((prev) => [...prev, `[${new Date().toLocaleTimeString()}] DTMF Digit '${digit}' -> ${choiceDesc}`]);

    try {
      const formData = new FormData();
      formData.append('Digits', digit);
      formData.append('From', '+919876543210');

      const res = await fetch(`${API_BASE}/api/voice/menu-select`, {
        method: 'POST',
        body: formData
      });
      const xmlText = await res.text();

      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
      const sayNodes = xmlDoc.getElementsByTagName('Say');
      const ackText = sayNodes.length > 0 ? sayNodes[0].textContent : `Emergency received for ${choiceDesc}. Immediate dispatch initiated.`;

      speakText(ackText, () => {
        setCallState('ENDED');
        setScreenMessage('DISPATCH CONFIRMED • CALL TERMINATED');
      });
    } catch (err) {
      console.error('DTMF menu select failed:', err);
    }
  };

  const handleSendVoiceSpeech = async () => {
    if (!voiceText.trim()) return;
    window.speechSynthesis.cancel();
    setCallState('RECORDING');
    setScreenMessage('PROCESSING WHISPER SPEECH-TO-TEXT...');
    setStatusLog((prev) => [...prev, `[${new Date().toLocaleTimeString()}] Speech Audio Buffer sent to Whisper STT`]);

    try {
      const formData = new FormData();
      formData.append('transcript_text', voiceText);

      const res = await fetch(`${API_BASE}/api/simulate/voice`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      setCallState('ENDED');
      setScreenMessage(`DISPATCHED: ${data.event.category} (SEV ${data.event.severity}/10)`);
      setStatusLog((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] Extracted Category: ${data.event.category}, Severity: ${data.event.severity}/10, Assigned: ${data.event.assigned_unit?.name || 'NDRF Unit'}`
      ]);

      speakText(`Emergency report captured. First responders have been dispatched to your sector.`);
    } catch (err) {
      console.error('Voice process failed:', err);
      setScreenMessage('VOICE PROCESS ERROR');
    }
  };

  const handleEndCall = () => {
    window.speechSynthesis.cancel();
    setCallState('IDLE');
    setScreenMessage('LINE READY: DIAL 112');
    setSelectedDigit(null);
    setStatusLog((prev) => [...prev, `[${new Date().toLocaleTimeString()}] Call Ended by Operator`]);
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="phone-sim-title"
      className="fixed inset-0 z-[4000] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
    >
      <div className="bg-[#0c121e] border border-[#25354e] w-full max-w-sm rounded shadow-2xl p-5 flex flex-col items-center relative text-slate-100 select-none">
        {/* Header */}
        <div className="w-full flex items-center justify-between pb-3 border-b border-[#1b2537] mb-3">
          <div className="flex items-center space-x-2">
            <Radio className="w-4 h-4 text-cyan-400" />
            <h2 id="phone-sim-title" className="text-xs font-bold uppercase tracking-wider text-slate-200 font-mono">
              2G Telecom Handset Simulator
            </h2>
          </div>
          <button
            onClick={() => {
              window.speechSynthesis.cancel();
              onClose();
            }}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-[#162030] transition"
            aria-label="Close Phone Simulator"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tactical Backlit LCD Display */}
        <div className="w-full bg-[#07130f] border border-[#1b3d30] rounded p-3 mb-3 font-mono">
          <div className="text-[10px] text-emerald-600 uppercase tracking-widest flex items-center justify-between mb-1">
            <span>GSM 900 MHz • 112 GATEWAY</span>
            <span className="flex items-center text-emerald-400">
              <Volume2 className={`w-3 h-3 mr-1 ${isSpeaking ? 'text-emerald-300' : 'opacity-40'}`} />
              {callState === 'CONNECTED' ? 'CARRIER ACTIVE' : 'STANDBY'}
            </span>
          </div>
          <div className="text-xs font-bold text-emerald-300 truncate">
            {screenMessage}
          </div>
          {selectedDigit && (
            <div className="text-[11px] text-amber-400 font-semibold mt-0.5">
              DTMF TONE SENT: [{selectedDigit}]
            </div>
          )}
        </div>

        {/* 3x4 Rugged Numeric Keypad */}
        <div className="grid grid-cols-3 gap-2 w-full mb-3">
          {[
            { num: '1', sub: 'POLICE' },
            { num: '2', sub: 'AMB' },
            { num: '3', sub: 'RESCUE' },
            { num: '4', sub: 'GHI' },
            { num: '5', sub: 'JKL' },
            { num: '6', sub: 'MNO' },
            { num: '7', sub: 'PQRS' },
            { num: '8', sub: 'TUV' },
            { num: '9', sub: 'WXYZ' },
            { num: '*', sub: 'CLEAR' },
            { num: '0', sub: '+' },
            { num: '#', sub: 'SEND' }
          ].map((k) => (
            <button
              key={k.num}
              onClick={() => handleKeypadPress(k.num)}
              disabled={callState !== 'CONNECTED'}
              className={`p-2 rounded border flex flex-col items-center justify-center transition active:scale-95 disabled:opacity-30 ${
                ['1', '2', '3'].includes(k.num) && callState === 'CONNECTED'
                  ? 'bg-[#1c283d] border-cyan-500 text-cyan-200 hover:bg-[#253652]'
                  : 'bg-[#101726] border-[#223046] text-slate-200 hover:bg-[#162032]'
              }`}
            >
              <span className="text-base font-bold font-mono leading-none">{k.num}</span>
              <span className="text-[8px] text-slate-400 tracking-wider font-mono mt-0.5">{k.sub}</span>
            </button>
          ))}
        </div>

        {/* Call Connect / Terminate Controls */}
        <div className="w-full mb-3">
          {callState === 'IDLE' || callState === 'ENDED' ? (
            <button
              onClick={handleStartCall}
              className="w-full py-2.5 rounded bg-emerald-700 hover:bg-emerald-600 text-white font-bold text-xs flex items-center justify-center space-x-2 transition active:scale-95"
            >
              <PhoneCall className="w-4 h-4" />
              <span>Connect Call (Dial 112)</span>
            </button>
          ) : (
            <button
              onClick={handleEndCall}
              className="w-full py-2.5 rounded bg-rose-700 hover:bg-rose-600 text-white font-bold text-xs flex items-center justify-center space-x-2 transition active:scale-95"
            >
              <PhoneOff className="w-4 h-4" />
              <span>Terminate Call</span>
            </button>
          )}
        </div>

        {/* Free-form Speech Option */}
        {callState === 'CONNECTED' && (
          <div className="w-full bg-[#101726] border border-[#233148] rounded p-2.5 space-y-1.5 text-xs mb-3">
            <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block font-mono">
              Alternative: Spoken Voice Report (Whisper STT):
            </span>
            <input
              type="text"
              value={voiceText}
              onChange={(e) => setVoiceText(e.target.value)}
              placeholder="Speak emergency report..."
              className="w-full px-2 py-1 bg-[#090d16] border border-[#233148] rounded text-slate-200 text-xs focus:outline-none focus:border-cyan-500 font-sans"
            />
            <button
              onClick={handleSendVoiceSpeech}
              className="w-full py-1 bg-[#16283d] hover:bg-[#1f3754] text-cyan-200 border border-[#2a4568] font-bold rounded text-[11px] flex items-center justify-center space-x-1"
            >
              <Mic className="w-3 h-3 text-cyan-400" />
              <span>Transmit Speech Message</span>
            </button>
          </div>
        )}

        {/* Transmission Log */}
        <div className="w-full bg-[#080c14] border border-[#1b2537] rounded p-2 max-h-20 overflow-y-auto font-mono text-[9px] text-slate-400 space-y-0.5">
          {statusLog.length === 0 ? (
            <div className="text-slate-600 italic">Standby. Click 'Connect Call' to initiate session.</div>
          ) : (
            statusLog.map((log, idx) => <div key={idx}>{log}</div>)
          )}
        </div>
      </div>
    </div>
  );
}
