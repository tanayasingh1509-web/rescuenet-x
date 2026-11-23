import React, { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, Circle } from 'react-leaflet';
import L from 'leaflet';
import mapboxgl from 'mapbox-gl';
import { Layers, Activity, Radio, Crosshair, ChevronDown, ChevronUp, Send, Globe, Satellite } from 'lucide-react';

// Fix Leaflet default icon issues in bundlers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Precision Tactical Leaflet Marker for Incidents
const createSeverityLeafletIcon = (category, severity) => {
  let color = '#38bdf8'; // Normal (1-4)
  if (severity >= 8) {
    color = '#ef4444'; // Critical (8-10)
  } else if (severity >= 5) {
    color = '#f59e0b'; // Elevated (5-7)
  }

  const isCritical = severity >= 8;

  const html = `
    <div style="position: relative; display: flex; align-items: center; justify-content: center; cursor: pointer;">
      ${isCritical ? `<div style="position: absolute; width: 34px; height: 34px; border-radius: 50%; background: ${color}; opacity: 0.3; animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>` : ''}
      <div style="
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: #090e17;
        border: 2px solid ${color};
        display: flex;
        align-items: center;
        justify-content: center;
        color: ${color};
        font-family: monospace;
        font-weight: 800;
        font-size: 11px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.8);
      ">
        ${severity}
      </div>
    </div>
  `;

  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: html,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    popupAnchor: [0, -13]
  });
};

// Tactical First Responder Fleet Marker (Square Chevron)
const createUnitLeafletIcon = (unitType) => {
  const colorMap = {
    'RESCUE': '#2563eb',
    'AMBULANCE': '#059669',
    'FIRE': '#ea580c',
    'POLICE': '#7c3aed'
  };
  const labelMap = {
    'RESCUE': 'RES',
    'AMBULANCE': 'EMS',
    'FIRE': 'FIR',
    'POLICE': 'POL'
  };
  const color = colorMap[unitType] || '#2563eb';
  const label = labelMap[unitType] || unitType.slice(0, 3);

  const html = `
    <div style="
      width: 28px;
      height: 18px;
      border-radius: 2px;
      background: #0a101d;
      border: 1.5px solid ${color};
      display: flex;
      align-items: center;
      justify-content: center;
      color: ${color};
      font-family: monospace;
      font-size: 9px;
      font-weight: 800;
      letter-spacing: 0.5px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.9);
      cursor: pointer;
    ">
      ${label}
    </div>
  `;
  return L.divIcon({
    className: 'custom-unit-marker',
    html: html,
    iconSize: [28, 18],
    iconAnchor: [14, 9]
  });
};

// Map Recenter Helper component for Leaflet
function ChangeView({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center && center[0] && center[1]) {
      map.setView(center, zoom, { animate: true });
    }
  }, [center, zoom, map]);
  return null;
}

// Tactical Dark Theme for Google Maps CAD Interface
const TACTICAL_DARK_STYLES = [
  { elementType: 'geometry', stylers: [{ color: '#090e18' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#090d16' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#7488a6' }] },
  {
    featureType: 'administrative.locality',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#94a3b8' }]
  },
  {
    featureType: 'poi',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#64748b' }]
  },
  {
    featureType: 'poi.park',
    elementType: 'geometry',
    stylers: [{ color: '#0b1626' }]
  },
  {
    featureType: 'road',
    elementType: 'geometry',
    stylers: [{ color: '#162234' }]
  },
  {
    featureType: 'road',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#101826' }]
  },
  {
    featureType: 'road',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#829ab8' }]
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry',
    stylers: [{ color: '#25354e' }]
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#172233' }]
  },
  {
    featureType: 'road.highway',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#9bb1d0' }]
  },
  {
    featureType: 'transit',
    elementType: 'geometry',
    stylers: [{ color: '#162234' }]
  },
  {
    featureType: 'transit.station',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#64748b' }]
  },
  {
    featureType: 'water',
    elementType: 'geometry',
    stylers: [{ color: '#060b14' }]
  },
  {
    featureType: 'water',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#3b4b63' }]
  },
  {
    featureType: 'water',
    elementType: 'labels.text.stroke',
    stylers: [{ color: '#060b14' }]
  }
];

// Asynchronous loader for Google Maps JavaScript SDK
const loadGoogleMapsScript = (apiKey) => {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined') return reject('No browser window');
    if (window.google && window.google.maps) {
      return resolve(window.google.maps);
    }
    const existing = document.getElementById('google-maps-sdk');
    if (existing) {
      existing.addEventListener('load', () => resolve(window.google.maps));
      existing.addEventListener('error', (err) => reject(err));
      return;
    }
    const script = document.createElement('script');
    script.id = 'google-maps-sdk';
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve(window.google.maps);
    script.onerror = (err) => reject(err);
    document.head.appendChild(script);
  });
};

export default function GISMap({
  events = [],
  units = [],
  selectedEvent,
  onSelectEvent,
  onDispatch,
  googleMapsApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || 'AIzaSyAOVYRIgupAurZup5y1PRh8Ismb1A3lLao',
  mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN || ''
}) {
  const [mapEngine, setMapEngine] = useState('google'); // 'google' | 'google-satellite' | 'leaflet' | 'mapbox'
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [isLegendOpen, setIsLegendOpen] = useState(true);
  const [googleMapsLoaded, setGoogleMapsLoaded] = useState(false);

  const googleContainerRef = useRef(null);
  const googleMapInstanceRef = useRef(null);
  const googleMarkersRef = useRef([]);
  const googleCirclesRef = useRef([]);

  const mapboxContainerRef = useRef(null);
  const mapboxInstanceRef = useRef(null);
  const mapboxMarkersRef = useRef([]);

  const defaultCenter = [28.6139, 77.2090];
  const center = selectedEvent && selectedEvent.coordinates
    ? [selectedEvent.coordinates.lat, selectedEvent.coordinates.lng]
    : defaultCenter;

  // 1. Initialize Google Maps Engine
  useEffect(() => {
    if ((mapEngine === 'google' || mapEngine === 'google-satellite') && googleMapsApiKey) {
      loadGoogleMapsScript(googleMapsApiKey)
        .then((maps) => {
          setGoogleMapsLoaded(true);
          if (googleContainerRef.current && !googleMapInstanceRef.current) {
            const isSat = mapEngine === 'google-satellite';
            const gMap = new maps.Map(googleContainerRef.current, {
              center: { lat: defaultCenter[0], lng: defaultCenter[1] },
              zoom: 13,
              mapTypeId: isSat ? 'hybrid' : 'roadmap',
              styles: isSat ? [] : TACTICAL_DARK_STYLES,
              disableDefaultUI: true,
              zoomControl: true,
              gestureHandling: 'greedy'
            });
            googleMapInstanceRef.current = gMap;
          } else if (googleMapInstanceRef.current) {
            // Update map type if already initialized
            const isSat = mapEngine === 'google-satellite';
            googleMapInstanceRef.current.setMapTypeId(isSat ? 'hybrid' : 'roadmap');
            googleMapInstanceRef.current.setOptions({
              styles: isSat ? [] : TACTICAL_DARK_STYLES
            });
          }
        })
        .catch((err) => {
          console.warn('Google Maps load failed, falling back to Leaflet:', err);
          setMapEngine('leaflet');
        });
    }
  }, [mapEngine, googleMapsApiKey]);

  // 2. Render Google Maps Markers and Hazard Circles
  useEffect(() => {
    if (!googleMapInstanceRef.current || !window.google || !window.google.maps) return;
    const gMap = googleMapInstanceRef.current;

    // Clear old Google markers and circles
    googleMarkersRef.current.forEach(m => m.setMap(null));
    googleMarkersRef.current = [];
    googleCirclesRef.current.forEach(c => c.setMap(null));
    googleCirclesRef.current = [];

    // Render Hazard Zones (Circles)
    if (showHeatmap) {
      events.forEach(ev => {
        if (!ev.coordinates || !ev.coordinates.lat || !ev.coordinates.lng) return;
        const color = ev.severity >= 8 ? '#ef4444' : (ev.severity >= 5 ? '#f59e0b' : '#38bdf8');
        const circle = new window.google.maps.Circle({
          strokeColor: color,
          strokeOpacity: 0.85,
          strokeWeight: 1,
          fillColor: color,
          fillOpacity: 0.16,
          map: gMap,
          center: { lat: ev.coordinates.lat, lng: ev.coordinates.lng },
          radius: ev.severity * 130
        });
        googleCirclesRef.current.push(circle);
      });
    }

    // Render Incident Markers
    events.forEach(ev => {
      if (!ev.coordinates || !ev.coordinates.lat || !ev.coordinates.lng) return;
      const color = ev.severity >= 8 ? '#ef4444' : (ev.severity >= 5 ? '#f59e0b' : '#38bdf8');
      
      const svgMarker = {
        url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
            <circle cx="14" cy="14" r="12" fill="#090e17" stroke="${color}" stroke-width="2.5" />
            <text x="14" y="18" fill="${color}" font-family="monospace, sans-serif" font-size="11" font-weight="bold" text-anchor="middle">${ev.severity}</text>
          </svg>
        `)}`,
        scaledSize: new window.google.maps.Size(28, 28),
        anchor: new window.google.maps.Point(14, 14)
      };

      const marker = new window.google.maps.Marker({
        position: { lat: ev.coordinates.lat, lng: ev.coordinates.lng },
        map: gMap,
        icon: svgMarker,
        title: `[SEV ${ev.severity}] ${ev.category} - ${ev.sector}`
      });

      marker.addListener('click', () => {
        onSelectEvent(ev);
      });

      googleMarkersRef.current.push(marker);
    });

    // Render First Responder Fleet Units
    units.forEach(u => {
      if (!u.lat || !u.lng) return;
      const colorMap = {
        'RESCUE': '#2563eb',
        'AMBULANCE': '#059669',
        'FIRE': '#ea580c',
        'POLICE': '#7c3aed'
      };
      const labelMap = {
        'RESCUE': 'RES',
        'AMBULANCE': 'EMS',
        'FIRE': 'FIR',
        'POLICE': 'POL'
      };
      const color = colorMap[u.unit_type] || '#2563eb';
      const label = labelMap[u.unit_type] || u.unit_type.slice(0, 3);

      const svgUnit = {
        url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
          <svg xmlns="http://www.w3.org/2000/svg" width="34" height="20" viewBox="0 0 34 20">
            <rect x="1" y="1" width="32" height="18" rx="2" fill="#0a101d" stroke="${color}" stroke-width="1.5" />
            <text x="17" y="14" fill="${color}" font-family="monospace, sans-serif" font-size="9" font-weight="bold" text-anchor="middle" letter-spacing="0.5">${label}</text>
          </svg>
        `)}`,
        scaledSize: new window.google.maps.Size(34, 20),
        anchor: new window.google.maps.Point(17, 10)
      };

      const marker = new window.google.maps.Marker({
        position: { lat: u.lat, lng: u.lng },
        map: gMap,
        icon: svgUnit,
        title: `UNIT: ${u.name} (${u.unit_type})`
      });

      googleMarkersRef.current.push(marker);
    });
  }, [events, units, showHeatmap, googleMapsLoaded, mapEngine, onSelectEvent]);

  // Recenter Google Map when selectedEvent changes
  useEffect(() => {
    if ((mapEngine === 'google' || mapEngine === 'google-satellite') && googleMapInstanceRef.current && selectedEvent && selectedEvent.coordinates) {
      googleMapInstanceRef.current.panTo({
        lat: selectedEvent.coordinates.lat,
        lng: selectedEvent.coordinates.lng
      });
      googleMapInstanceRef.current.setZoom(14);
    }
  }, [selectedEvent, mapEngine]);

  // 3. Initialize Mapbox if selected and token is available
  useEffect(() => {
    if (mapEngine === 'mapbox' && mapboxToken) {
      try {
        mapboxgl.accessToken = mapboxToken;
        const mb = new mapboxgl.Map({
          container: mapboxContainerRef.current,
          style: 'mapbox://styles/mapbox/dark-v11',
          center: [defaultCenter[1], defaultCenter[0]],
          zoom: 13
        });

        mb.addControl(new mapboxgl.NavigationControl(), 'top-right');
        mapboxInstanceRef.current = mb;

        return () => {
          mb.remove();
        };
      } catch (err) {
        console.warn('Mapbox initialization failed, falling back to Leaflet:', err);
        setMapEngine('leaflet');
      }
    }
  }, [mapEngine, mapboxToken]);

  // Update Mapbox markers when events change
  useEffect(() => {
    if (mapEngine === 'mapbox' && mapboxInstanceRef.current) {
      mapboxMarkersRef.current.forEach(m => m.remove());
      mapboxMarkersRef.current = [];

      events.forEach(ev => {
        if (!ev.coordinates) return;
        const el = document.createElement('div');
        el.className = 'radar-ping';
        const color = ev.severity >= 8 ? '#ef4444' : (ev.severity >= 5 ? '#f59e0b' : '#38bdf8');
        el.innerHTML = `
          <div style="
            width: 22px; height: 22px; border-radius: 50%;
            background: #090e17; border: 2px solid ${color};
            color: ${color}; display: flex; align-items: center;
            justify-content: center; font-weight: bold; font-size: 11px;
            box-shadow: 0 0 6px ${color}; cursor: pointer;
          ">${ev.severity}</div>
        `;
        el.addEventListener('click', () => onSelectEvent(ev));

        const marker = new mapboxgl.Marker(el)
          .setLngLat([ev.coordinates.lng, ev.coordinates.lat])
          .addTo(mapboxInstanceRef.current);
        mapboxMarkersRef.current.push(marker);
      });
    }
  }, [events, mapEngine, onSelectEvent]);

  return (
    <div className="relative w-full h-full rounded border border-[#1b2638] overflow-hidden bg-[#090d16] select-none">
      {/* Precision Map Toolbar (Top-Left) */}
      <div className="absolute top-3 left-3 z-[1000] flex items-center space-x-1.5 bg-[#0d1422] border border-[#1e2a3e] px-2 py-1.5 rounded text-xs shadow-lg">
        <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider pr-1 border-r border-[#1f2b3e] flex items-center space-x-1">
          <Globe className="w-3 h-3 text-emerald-400" />
          <span>GIS ENGINE</span>
        </span>

        {/* Google Maps (Dark Tactical) */}
        <button
          onClick={() => setMapEngine('google')}
          className={`px-2 py-0.5 rounded text-[11px] font-medium transition flex items-center space-x-1 ${
            mapEngine === 'google'
              ? 'bg-[#1b2638] text-white font-bold border border-emerald-500/60 shadow-sm'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          title="Google Maps Tactical Dark (Active Projection)"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span>Google Dark</span>
        </button>

        {/* Google Maps Satellite */}
        <button
          onClick={() => setMapEngine('google-satellite')}
          className={`px-2 py-0.5 rounded text-[11px] font-medium transition flex items-center space-x-1 ${
            mapEngine === 'google-satellite'
              ? 'bg-[#1b2638] text-white font-bold border border-sky-500/60 shadow-sm'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          title="Google Maps Aerial Satellite Imagery"
        >
          <Satellite className="w-3 h-3 text-sky-400" />
          <span>Satellite</span>
        </button>

        {/* Leaflet Carto Dark (Offline) */}
        <button
          onClick={() => setMapEngine('leaflet')}
          className={`px-2 py-0.5 rounded text-[11px] font-medium transition ${
            mapEngine === 'leaflet'
              ? 'bg-[#1b2638] text-white font-bold border border-[#2d3e5a]'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          title="OpenStreetMap / CARTO Offline Fallback"
        >
          Carto Dark
        </button>

        {/* Mapbox Vector */}
        <button
          onClick={() => {
            if (!mapboxToken) {
              alert('Notice: Mapbox access token not set. Running on Google Maps or Carto Dark.');
            } else {
              setMapEngine('mapbox');
            }
          }}
          className={`px-2 py-0.5 rounded text-[11px] font-medium transition ${
            mapEngine === 'mapbox'
              ? 'bg-[#1b2638] text-white font-bold border border-[#2d3e5a]'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Mapbox
        </button>

        <span className="w-px h-3 bg-[#1f2b3e]" />

        {/* Heatmap Layer Toggle */}
        <button
          onClick={() => setShowHeatmap(!showHeatmap)}
          className={`px-2 py-0.5 rounded text-[11px] font-medium transition flex items-center space-x-1.5 ${
            showHeatmap
              ? 'bg-[#291316] text-rose-300 border border-rose-800'
              : 'text-slate-400 hover:text-slate-200 bg-[#121a28]'
          }`}
          title="Toggle Hazard Density Overlay"
        >
          <span className={`w-1.5 h-1.5 rounded-full ${showHeatmap ? 'bg-rose-400' : 'bg-slate-500'}`} />
          <span>Hazard Radius: {showHeatmap ? 'ON' : 'OFF'}</span>
        </button>
      </div>

      {/* Map Rendering Container */}
      {(mapEngine === 'google' || mapEngine === 'google-satellite') ? (
        <div ref={googleContainerRef} className="w-full h-full bg-[#090d16]" />
      ) : mapEngine === 'mapbox' ? (
        <div ref={mapboxContainerRef} className="w-full h-full" />
      ) : (
        <MapContainer
          center={defaultCenter}
          zoom={13}
          style={{ width: '100%', height: '100%', backgroundColor: '#090d16' }}
          zoomControl={false}
        >
          <ChangeView center={center} zoom={selectedEvent ? 14 : 13} />
          {/* CartoDB Dark Tactical Tiles */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* Crisis Hazard Heatmap Zones */}
          {showHeatmap && events.map((ev) => {
            if (!ev.coordinates || !ev.coordinates.lat || !ev.coordinates.lng) return null;
            const isCritical = ev.severity >= 8;
            const heatColor = isCritical ? '#ef4444' : (ev.severity >= 5 ? '#f59e0b' : '#38bdf8');
            return (
              <Circle
                key={`heat-${ev.id}`}
                center={[ev.coordinates.lat, ev.coordinates.lng]}
                radius={ev.severity * 130}
                pathOptions={{
                  fillColor: heatColor,
                  fillOpacity: 0.16,
                  color: heatColor,
                  weight: 1,
                  dashArray: '4, 4'
                }}
              />
            );
          })}

          {/* Incident Event Markers */}
          {events.map((ev) => {
            if (!ev.coordinates || !ev.coordinates.lat || !ev.coordinates.lng) return null;
            return (
              <Marker
                key={ev.id}
                position={[ev.coordinates.lat, ev.coordinates.lng]}
                icon={createSeverityLeafletIcon(ev.category, ev.severity)}
                eventHandlers={{
                  click: () => onSelectEvent(ev),
                }}
              >
                <Popup>
                  <div className="p-1 min-w-[220px]">
                    <div className="flex items-center justify-between pb-1.5 border-b border-[#283850] mb-1.5">
                      <span className="font-bold text-xs uppercase tracking-wider text-rose-400 font-mono">
                        {ev.category}
                      </span>
                      <span className="text-[10px] font-mono bg-[#162030] text-slate-300 px-1.5 py-0.5 rounded border border-[#273752]">
                        SEV {ev.severity}/10
                      </span>
                    </div>

                    <div className="text-xs font-semibold text-slate-100 mb-1">{ev.sector}</div>
                    <div className="text-[11px] text-slate-300 line-clamp-2 mb-2 leading-relaxed">
                      {ev.summary}
                    </div>

                    <div className="flex items-center justify-between pt-1 border-t border-[#1e2a3e] text-[10px]">
                      <span className="text-slate-400 font-mono">
                        {ev.assigned_unit ? ev.assigned_unit.name.split(' ')[0] : 'UNASSIGNED'}
                      </span>
                      <button
                        onClick={() => onDispatch(ev.id)}
                        className="bg-rose-700 hover:bg-rose-600 text-white px-2 py-0.5 rounded font-bold transition flex items-center space-x-1"
                      >
                        <Send className="w-2.5 h-2.5" />
                        <span>Dispatch</span>
                      </button>
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* Rescue Unit Fleet Markers */}
          {units.map((u) => (
            <Marker
              key={u.id}
              position={[u.lat, u.lng]}
              icon={createUnitLeafletIcon(u.unit_type)}
            >
              <Popup>
                <div className="p-1 text-xs">
                  <div className="font-bold text-slate-100">{u.name}</div>
                  <div className="text-[11px] text-slate-400 font-mono">CODE: {u.id}</div>
                  <div className="text-emerald-400 font-semibold mt-1">STATUS: {u.status}</div>
                  <div className="text-slate-400 text-[10px]">FREQ: 142.55 MHz</div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      )}

      {/* Collapsible Tactical Legend (Bottom-Right) */}
      <div className="absolute bottom-3 right-3 z-[1000] bg-[#0d1422] border border-[#1e2a3e] rounded text-[11px] text-slate-300 shadow-xl">
        <div
          onClick={() => setIsLegendOpen(!isLegendOpen)}
          className="flex items-center justify-between px-2.5 py-1.5 cursor-pointer font-semibold text-xs text-slate-200 border-b border-[#1b2638]"
        >
          <span className="text-[10px] uppercase tracking-wider font-mono text-slate-400">Map Legend</span>
          {isLegendOpen ? <ChevronDown className="w-3.5 h-3.5 text-slate-400" /> : <ChevronUp className="w-3.5 h-3.5 text-slate-400" />}
        </div>

        {isLegendOpen && (
          <div className="p-2.5 space-y-1.5 font-mono text-[10px]">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-rose-500"></span>
              <span>Priority 1 (Sev 8-10)</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-amber-500"></span>
              <span>Priority 2 (Sev 5-7)</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-sky-400"></span>
              <span>Monitored (Sev 1-4)</span>
            </div>
            <div className="flex items-center space-x-2 pt-1 border-t border-[#1b2638]">
              <span className="w-3 h-2 rounded bg-[#0a101d] border border-blue-500"></span>
              <span>CAD Units (RES/EMS/FIR)</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
