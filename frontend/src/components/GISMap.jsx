import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, Circle, Polyline } from 'react-leaflet';
import L from 'leaflet';
import { ChevronDown, ChevronUp, Send, Globe, Satellite } from 'lucide-react';

// Fix Leaflet default icon issues offline using self-contained inline SVG data URIs
delete L.Icon.Default.prototype._getIconUrl;
const DEFAULT_MARKER_SVG = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
  <svg xmlns="http://www.w3.org/2000/svg" width="25" height="41" viewBox="0 0 25 41">
    <path fill="#2563eb" stroke="#ffffff" stroke-width="1.5" d="M12.5 0C5.6 0 0 5.6 0 12.5c0 9.4 12.5 28.5 12.5 28.5S25 21.9 25 12.5C25 5.6 19.4 0 12.5 0z"/>
    <circle cx="12.5" cy="12.5" r="5" fill="#ffffff"/>
  </svg>
`)}`;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: DEFAULT_MARKER_SVG,
  iconUrl: DEFAULT_MARKER_SVG,
  shadowUrl: '',
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

// Asynchronous loader for Google Maps JavaScript SDK (No libraries=places)
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
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}`;
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
  googleMapsApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || ''
}) {
  const [mapEngine, setMapEngine] = useState(googleMapsApiKey ? 'google' : 'leaflet');
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [isLegendOpen, setIsLegendOpen] = useState(true);
  const [googleMapsLoaded, setGoogleMapsLoaded] = useState(false);

  const googleContainerRef = useRef(null);
  const googleMapInstanceRef = useRef(null);

  // Marker diffing maps to prevent flickering
  const googleIncidentMarkersRef = useRef(new Map());
  const googleUnitMarkersRef = useRef(new Map());
  const googleCirclesRef = useRef(new Map());
  const googlePolylinesRef = useRef(new Map());

  const defaultCenter = useMemo(() => [28.6139, 77.2090], []);
  const center = useMemo(() => {
    if (selectedEvent && selectedEvent.coordinates && selectedEvent.coordinates.lat && selectedEvent.coordinates.lng) {
      return [selectedEvent.coordinates.lat, selectedEvent.coordinates.lng];
    }
    return defaultCenter;
  }, [selectedEvent, defaultCenter]);

  // Clean teardown for Google Maps
  const teardownGoogleMap = useCallback(() => {
    googleIncidentMarkersRef.current.forEach((m) => m.setMap(null));
    googleIncidentMarkersRef.current.clear();

    googleUnitMarkersRef.current.forEach((m) => m.setMap(null));
    googleUnitMarkersRef.current.clear();

    googleCirclesRef.current.forEach((c) => c.setMap(null));
    googleCirclesRef.current.clear();

    googlePolylinesRef.current.forEach((p) => p.setMap(null));
    googlePolylinesRef.current.clear();

    googleMapInstanceRef.current = null;
    setGoogleMapsLoaded(false);

    if (googleContainerRef.current) {
      googleContainerRef.current.innerHTML = '';
    }

    const script = document.getElementById('google-maps-sdk');
    if (script && script.parentNode) {
      script.parentNode.removeChild(script);
    }
  }, []);

  // Global handler for Google Maps authentication failures
  useEffect(() => {
    window.gm_authFailure = () => {
      console.warn('Google Maps authentication failed (gm_authFailure). Falling back to Leaflet Carto Dark.');
      teardownGoogleMap();
      setMapEngine('leaflet');
    };

    return () => {
      delete window.gm_authFailure;
    };
  }, [teardownGoogleMap]);

  // Handle engine switching & Google Maps initialization
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
            const isSat = mapEngine === 'google-satellite';
            googleMapInstanceRef.current.setMapTypeId(isSat ? 'hybrid' : 'roadmap');
            googleMapInstanceRef.current.setOptions({
              styles: isSat ? [] : TACTICAL_DARK_STYLES
            });
          }
        })
        .catch((err) => {
          console.warn('Google Maps load failed, falling back to Leaflet:', err);
          teardownGoogleMap();
          setMapEngine('leaflet');
        });
    } else if (mapEngine === 'leaflet' || mapEngine === 'leaflet-satellite') {
      teardownGoogleMap();
    }
  }, [mapEngine, googleMapsApiKey, defaultCenter, teardownGoogleMap]);

  // Map of units by ID for quick lookup
  const unitMap = useMemo(() => {
    const map = new Map();
    units.forEach((u) => map.set(u.id, u));
    return map;
  }, [units]);

  // Diffing and updating Google Maps markers & polylines
  useEffect(() => {
    if (!googleMapInstanceRef.current || !window.google || !window.google.maps) return;
    const gMap = googleMapInstanceRef.current;
    const gMaps = window.google.maps;

    // 1. Diff Incident Markers
    const currentEventIds = new Set();
    events.forEach((ev) => {
      if (!ev.coordinates || !ev.coordinates.lat || !ev.coordinates.lng) return;
      currentEventIds.add(ev.id);
      const pos = { lat: ev.coordinates.lat, lng: ev.coordinates.lng };
      const color = ev.severity >= 8 ? '#ef4444' : ev.severity >= 5 ? '#f59e0b' : '#38bdf8';

      const svgMarker = {
        url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
            <circle cx="14" cy="14" r="12" fill="#090e17" stroke="${color}" stroke-width="2.5" />
            <text x="14" y="18" fill="${color}" font-family="monospace, sans-serif" font-size="11" font-weight="bold" text-anchor="middle">${ev.severity}</text>
          </svg>
        `)}`,
        scaledSize: new gMaps.Size(28, 28),
        anchor: new gMaps.Point(14, 14)
      };

      if (googleIncidentMarkersRef.current.has(ev.id)) {
        const marker = googleIncidentMarkersRef.current.get(ev.id);
        marker.setPosition(pos);
        marker.setIcon(svgMarker);
        marker.setTitle(`[SEV ${ev.severity}] ${ev.category} - ${ev.sector}`);
      } else {
        const marker = new gMaps.Marker({
          position: pos,
          map: gMap,
          icon: svgMarker,
          title: `[SEV ${ev.severity}] ${ev.category} - ${ev.sector}`
        });
        marker.addListener('click', () => onSelectEvent(ev));
        googleIncidentMarkersRef.current.set(ev.id, marker);
      }
    });

    // Remove deleted incident markers
    googleIncidentMarkersRef.current.forEach((marker, id) => {
      if (!currentEventIds.has(id)) {
        marker.setMap(null);
        googleIncidentMarkersRef.current.delete(id);
      }
    });

    // 2. Diff Unit Fleet Markers
    const currentUnitIds = new Set();
    units.forEach((u) => {
      if (!u.lat || !u.lng) return;
      currentUnitIds.add(u.id);
      const pos = { lat: u.lat, lng: u.lng };
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
        scaledSize: new gMaps.Size(34, 20),
        anchor: new gMaps.Point(17, 10)
      };

      if (googleUnitMarkersRef.current.has(u.id)) {
        const marker = googleUnitMarkersRef.current.get(u.id);
        marker.setPosition(pos);
        marker.setIcon(svgUnit);
        marker.setTitle(`UNIT: ${u.name} (${u.unit_type}) [${u.status}]`);
      } else {
        const marker = new gMaps.Marker({
          position: pos,
          map: gMap,
          icon: svgUnit,
          title: `UNIT: ${u.name} (${u.unit_type}) [${u.status}]`
        });
        googleUnitMarkersRef.current.set(u.id, marker);
      }
    });

    // Remove deleted unit markers
    googleUnitMarkersRef.current.forEach((marker, id) => {
      if (!currentUnitIds.has(id)) {
        marker.setMap(null);
        googleUnitMarkersRef.current.delete(id);
      }
    });

    // 3. Diff Routing Polylines (Assigned Unit -> Incident)
    const activeRouteIds = new Set();
    events.forEach((ev) => {
      if (!ev.coordinates || !ev.assigned_unit) return;
      const assigned = unitMap.get(ev.assigned_unit.id) || ev.assigned_unit;
      if (!assigned.lat || !assigned.lng) return;

      const routeKey = `route_${ev.id}_${assigned.id}`;
      activeRouteIds.add(routeKey);

      const path = [
        { lat: assigned.lat, lng: assigned.lng },
        { lat: ev.coordinates.lat, lng: ev.coordinates.lng }
      ];

      if (googlePolylinesRef.current.has(routeKey)) {
        const polyline = googlePolylinesRef.current.get(routeKey);
        polyline.setPath(path);
      } else {
        const polyline = new gMaps.Polyline({
          path,
          geodesic: true,
          strokeColor: '#38bdf8',
          strokeOpacity: 0.85,
          strokeWeight: 2.5,
          map: gMap
        });
        googlePolylinesRef.current.set(routeKey, polyline);
      }
    });

    // Remove obsolete polylines
    googlePolylinesRef.current.forEach((polyline, id) => {
      if (!activeRouteIds.has(id)) {
        polyline.setMap(null);
        googlePolylinesRef.current.delete(id);
      }
    });

    // 4. Diff Hazard Zone Circles
    const activeCircleIds = new Set();
    if (showHeatmap) {
      events.forEach((ev) => {
        if (!ev.coordinates || !ev.coordinates.lat || !ev.coordinates.lng) return;
        activeCircleIds.add(ev.id);
        const color = ev.severity >= 8 ? '#ef4444' : ev.severity >= 5 ? '#f59e0b' : '#38bdf8';
        const centerPos = { lat: ev.coordinates.lat, lng: ev.coordinates.lng };
        const radius = ev.severity * 130;

        if (googleCirclesRef.current.has(ev.id)) {
          const circle = googleCirclesRef.current.get(ev.id);
          circle.setCenter(centerPos);
          circle.setRadius(radius);
          circle.setOptions({ strokeColor: color, fillColor: color });
        } else {
          const circle = new gMaps.Circle({
            strokeColor: color,
            strokeOpacity: 0.85,
            strokeWeight: 1,
            fillColor: color,
            fillOpacity: 0.16,
            map: gMap,
            center: centerPos,
            radius: radius
          });
          googleCirclesRef.current.set(ev.id, circle);
        }
      });
    }

    // Clean up disabled or deleted circles
    googleCirclesRef.current.forEach((circle, id) => {
      if (!activeCircleIds.has(id)) {
        circle.setMap(null);
        googleCirclesRef.current.delete(id);
      }
    });
  }, [events, units, showHeatmap, googleMapsLoaded, mapEngine, onSelectEvent, unitMap]);

  // Recenter Google Map when selectedEvent changes
  useEffect(() => {
    if (
      (mapEngine === 'google' || mapEngine === 'google-satellite') &&
      googleMapInstanceRef.current &&
      selectedEvent &&
      selectedEvent.coordinates
    ) {
      googleMapInstanceRef.current.panTo({
        lat: selectedEvent.coordinates.lat,
        lng: selectedEvent.coordinates.lng
      });
      googleMapInstanceRef.current.setZoom(14);
    }
  }, [selectedEvent, mapEngine]);

  return (
    <div className="relative w-full h-full rounded border border-[#1b2638] overflow-hidden bg-[#090d16]">
      {/* Precision Map Toolbar (Top-Left) */}
      <div className="absolute top-3 left-3 z-[1000] flex items-center space-x-1.5 bg-[#0d1422] border border-[#1e2a3e] px-2 py-1.5 rounded text-xs shadow-lg">
        <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider pr-1 border-r border-[#1f2b3e] flex items-center space-x-1">
          <Globe className="w-3 h-3 text-emerald-400" />
          <span>GIS ENGINE</span>
        </span>

        {/* Keyless engines: always available, no API key needed */}
        <button
          onClick={() => setMapEngine('leaflet')}
          className={`px-2 py-0.5 rounded text-[11px] font-medium transition ${
            mapEngine === 'leaflet'
              ? 'bg-[#1b2638] text-white font-bold border border-emerald-500/60 shadow-sm'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          title="CARTO Dark tactical basemap (no API key required)"
          aria-label="Switch to Carto Dark map"
        >
          Carto Dark
        </button>

        <button
          onClick={() => setMapEngine('leaflet-satellite')}
          className={`px-2 py-0.5 rounded text-[11px] font-medium transition flex items-center space-x-1 ${
            mapEngine === 'leaflet-satellite'
              ? 'bg-[#1b2638] text-white font-bold border border-sky-500/60 shadow-sm'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          title="Esri World Imagery satellite (no API key required)"
          aria-label="Switch to satellite imagery map"
        >
          <Satellite className="w-3 h-3 text-sky-400" />
          <span>Satellite</span>
        </button>

        {/* Google engines: only offered when a Maps key is actually configured */}
        {googleMapsApiKey && (
          <>
            <button
              onClick={() => setMapEngine('google')}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition flex items-center space-x-1 ${
                mapEngine === 'google'
                  ? 'bg-[#1b2638] text-white font-bold border border-emerald-500/60 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Google Maps Tactical Dark"
              aria-label="Switch to Google Maps Dark engine"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>Google Dark</span>
            </button>

            <button
              onClick={() => setMapEngine('google-satellite')}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition flex items-center space-x-1 ${
                mapEngine === 'google-satellite'
                  ? 'bg-[#1b2638] text-white font-bold border border-sky-500/60 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Google Maps Aerial Satellite Imagery"
              aria-label="Switch to Google Maps Satellite engine"
            >
              <Satellite className="w-3 h-3 text-sky-400" />
              <span>Google Sat</span>
            </button>
          </>
        )}

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
          aria-label="Toggle Hazard Density Overlay"
        >
          <span className={`w-1.5 h-1.5 rounded-full ${showHeatmap ? 'bg-rose-400' : 'bg-slate-500'}`} />
          <span>Hazard Radius: {showHeatmap ? 'ON' : 'OFF'}</span>
        </button>
      </div>

      {/* Map Rendering Container */}
      {mapEngine === 'google' || mapEngine === 'google-satellite' ? (
        <div ref={googleContainerRef} className="w-full h-full bg-[#090d16]" />
      ) : (
        <MapContainer
          center={defaultCenter}
          zoom={13}
          style={{ width: '100%', height: '100%', backgroundColor: '#090d16' }}
          zoomControl={false}
        >
          <ChangeView center={center} zoom={selectedEvent ? 14 : 13} />

          {/* Keyless basemaps: CARTO Dark (default) or Esri World Imagery */}
          {mapEngine === 'leaflet-satellite' ? (
            <TileLayer
              key="esri-satellite"
              attribution="Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              maxZoom={19}
            />
          ) : (
            <TileLayer
              key="carto-dark"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
          )}

          {/* Crisis Hazard Heatmap Zones */}
          {showHeatmap &&
            events.map((ev) => {
              if (!ev.coordinates || !ev.coordinates.lat || !ev.coordinates.lng) return null;
              const isCritical = ev.severity >= 8;
              const heatColor = isCritical ? '#ef4444' : ev.severity >= 5 ? '#f59e0b' : '#38bdf8';
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

          {/* Visual Tactical Routing Lines (Assigned Unit -> Incident) */}
          {events.map((ev) => {
            if (!ev.coordinates || !ev.assigned_unit) return null;
            const assigned = unitMap.get(ev.assigned_unit.id) || ev.assigned_unit;
            if (!assigned.lat || !assigned.lng) return null;

            return (
              <Polyline
                key={`route-${ev.id}-${assigned.id}`}
                positions={[
                  [assigned.lat, assigned.lng],
                  [ev.coordinates.lat, ev.coordinates.lng]
                ]}
                pathOptions={{
                  color: '#38bdf8',
                  weight: 2.5,
                  dashArray: '6, 6',
                  opacity: 0.85
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
                  click: () => onSelectEvent(ev)
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
                        aria-label={`Dispatch unit to incident ${ev.id}`}
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
          role="button"
          tabIndex={0}
          aria-expanded={isLegendOpen}
          aria-label="Toggle Tactical Map Legend"
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') setIsLegendOpen(!isLegendOpen);
          }}
        >
          <span className="text-[10px] uppercase tracking-wider font-mono text-slate-400">Map Legend</span>
          {isLegendOpen ? <ChevronDown className="w-3.5 h-3.5 text-slate-400" /> : <ChevronUp className="w-3.5 h-3.5 text-slate-400" />}
        </div>

        {isLegendOpen && (
          <div className="p-2.5 space-y-1.5 font-mono text-[10px] select-text">
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
            <div className="flex items-center space-x-2">
              <span className="w-4 h-0.5 border-t border-dashed border-sky-400"></span>
              <span>Dispatch Vector (Unit &rarr; Scene)</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
