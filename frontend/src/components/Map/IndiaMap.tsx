import React, { useEffect, useCallback, useRef, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, GeoJSON, useMap } from 'react-leaflet';
import * as L from 'leaflet';
import { useApp } from '../../store/AppContext';
import { CityData, RiskLevel, CrimeDataPoint } from '../../types';
import { useThreatContext } from '../../store/ThreatContext';
import indiaStatesGeoJSON from '../../utils/indiaStatesGeoJSON';

import { BoltIcon, FlameIcon, GraphIcon, HomeIcon, SearchIcon, ShieldIcon, CloseIcon } from '../Icons/Icons';
import { VectorDetailModal, VectorLike } from '../VectorDetailModal/VectorDetailModal';
import DataSourcesPanel from '../DataSourcesPanel/DataSourcesPanel';

// GeoJSON Feature type for India states map
interface GeoFeature extends GeoJSON.Feature<GeoJSON.Geometry> {}

const SVG_NS = 'http://www.w3.org/2000/svg';

// ==================== Color Constants ====================

const riskColors: Record<RiskLevel, string> = {
  safe: '#22c55e',
  medium: '#eab308',
  critical: '#ef4444',
};

const riskFillColors: Record<RiskLevel, string> = {
  safe: 'rgba(34, 197, 94, 0.2)',
  medium: 'rgba(234, 179, 8, 0.3)',
  critical: 'rgba(239, 68, 68, 0.4)',
};

const riskRadius: Record<RiskLevel, number> = {
  safe: 7,
  medium: 10,
  critical: 14,
};

// Country flag emoji mapping for origin intelligence
const COUNTRY_FLAGS: Record<string, string> = {
  'Pakistan': '🇵🇰',
  'China': '🇨🇳',
  'North Korea': '🇰🇵',
  'Russia': '🇷🇺',
  'Iran': '🇮🇷',
  'USA': '🇺🇸',
  'India': '🇮🇳',
  'Unknown': '🏴',
};

// Source feed color mapping
const FEED_COLORS: Record<string, string> = {
  'ThreatFox': '#8b5cf6',
  'Feodo': '#06b6d4',
  'IPsum': '#5a6a80',
};

const FEED_LABELS: Record<string, string> = {
  'ThreatFox': 'TF',
  'Feodo': 'FD',
  'IPsum': 'IP',
};

// ==================== City Marker ====================

function CityMarker({ city }: { city: CityData & { note?: string } }) {
  const { dispatch } = useApp();
  const color = riskColors[city.risk];
  const fillColor = riskFillColors[city.risk];

  const handleClick = useCallback(() => {
    dispatch({ type: 'SET_SELECTED_CITY', payload: city });
    dispatch({ type: 'SET_MAP_CENTER', payload: [city.lat, city.lng] });
    dispatch({ type: 'SET_MAP_ZOOM', payload: 8 });
  }, [city, dispatch]);

  return (
    <CircleMarker
      center={[city.lat, city.lng]}
      radius={riskRadius[city.risk]}
      pathOptions={{
        color,
        fillColor,
        fillOpacity: 0.6,
        weight: 2,
      }}
      eventHandlers={{ click: handleClick }}
    >
      <Popup>
        <div className="city-popup">
          <h3>{city.name}</h3>
          <span className="risk-badge" style={{
            background: `${color}22`,
            color,
            border: `1px solid ${color}`,
          }}>
            {city.risk.toUpperCase()} RISK
          </span>
          <div className="stats">
            <div>Assets: {city.assetCount.toLocaleString()}</div>
            <div>Active Threats: {city.activeThreats} <span style={{ fontSize:9, color:'var(--text-muted)' }}>(estimated)</span></div>
          </div>
        </div>
      </Popup>
    </CircleMarker>
  );
}

// ==================== Destination Pins (Attack Target Markers) ====================

function DestinationPins({ vectors, onSelectVector }: { vectors: VectorLike[]; onSelectVector?: (v: VectorLike) => void }) {
  const destinationGroups = React.useMemo(() => {
    const groups = new Map<string, { vectors: VectorLike[]; lat: number; lng: number; severity: string }>();
    vectors.forEach(v => {
      const key = v.to;
      const existing = groups.get(key);
      if (existing) {
        existing.vectors.push(v);
        if (v.severity === 'critical' || (v.severity === 'medium' && existing.severity !== 'critical')) {
          existing.severity = v.severity;
        }
      } else {
        groups.set(key, {
          vectors: [v],
          lat: v.toLat,
          lng: v.toLng,
          severity: v.severity,
        });
      }
    });
    return Array.from(groups.entries()).map(([city, data]) => ({ city, ...data }));
  }, [vectors]);

  if (vectors.length === 0 || destinationGroups.length === 0) return null;

  return (
    <>
      {destinationGroups.map(dg => (          <DestinationPin
            key={dg.city}
            city={dg.city}
            lat={dg.lat}
            lng={dg.lng}
            count={dg.vectors.length}
            severity={dg.severity as RiskLevel}
            vectors={dg.vectors}
          />
      ))}
    </>
  );
}

function DestinationPin({ city, lat, lng, count, severity, vectors }: {
  city: string;
  lat: number;
  lng: number;
  count: number;
  severity: RiskLevel;
  vectors: VectorLike[];
}) {
  // Skip rendering if coordinates are invalid (MUST be before any hooks for Rules of Hooks)
  if (!lat && !lng) return null;

  const color = riskColors[severity];
  const [isPulsing, setIsPulsing] = useState(false);

  // Pulse for critical destinations
  useEffect(() => {
    if (severity !== 'critical') return;
    const interval = setInterval(() => {
      setIsPulsing(p => !p);
    }, 800);
    return () => clearInterval(interval);
  }, [severity]);

  // Size based on count and severity
  const baseRadius = severity === 'critical' ? 12 : 9;
  const radius = baseRadius + Math.min(count - 1, 5) * 1.5;

  // Group real data: origin countries and attack types
  const originCountries = [...new Set(vectors.map(v => v.from))];
  const attackTypes = [...new Set(vectors.map(v => v.attackType))];
  const feeds = [...new Set(vectors.map(v => v.source).filter(Boolean))];
  const totalCritical = vectors.filter(v => v.severity === 'critical').length;

  return (
    <CircleMarker
      center={[lat, lng]}
      radius={radius}
      pathOptions={{
        color,
        fillColor: severity === 'critical'
          ? (isPulsing ? '#ef444480' : color)
          : color,
        fillOpacity: severity === 'critical' ? (isPulsing ? 0.9 : 0.7) : 0.7,
        weight: count > 1 ? 3 : 2,
      }}
    >
      <Popup>
        <div className="city-popup" style={{minWidth: 200, padding: 4}}>
          {/* Real data: feed acknowledgement */}
          <div style={{display:'flex', alignItems:'center', gap:6, marginBottom:6, justifyContent:'center'}}>
            <span style={{fontSize:14}}>🛡️</span>
            <span style={{fontSize:10, fontWeight:700, color:'var(--accent-cyan)', letterSpacing:1}}>THREAT FEED</span>
          </div>

          {/* Live attack count — the only metric that matters here */}
          <div style={{fontSize:22, fontWeight:800, color, fontFamily:'JetBrains Mono, monospace', textAlign:'center', marginBottom:4}}>
            {count}
          </div>
          <div style={{fontSize:10, color:'var(--text-secondary)', textAlign:'center', marginBottom:8, fontWeight:600}}>
            Live Threat Vector{count > 1 ? 's' : ''} Detected
            {totalCritical > 0 && (
              <span style={{color:'var(--accent-red)'}}> · {totalCritical} Critical</span>
            )}
          </div>

          {/* Real data: origin + attack types */}
          <div style={{background:'rgba(8,12,24,0.5)', borderRadius:6, padding:'6px 8px', marginBottom:6}}>
            {originCountries.length > 0 && (
              <div style={{display:'flex', alignItems:'center', gap:4, marginBottom:3, fontSize:10}}>
                <span style={{color:'var(--text-muted)', fontWeight:600}}>Origins:</span>
                <span style={{color:'var(--text-primary)'}}>
                  {originCountries.map(c => `${COUNTRY_FLAGS[c] || '🏴'} ${c}`).join(', ')}
                </span>
              </div>
            )}
            {attackTypes.length > 0 && (
              <div style={{display:'flex', alignItems:'center', gap:4, fontSize:10}}>
                <span style={{color:'var(--text-muted)', fontWeight:600}}>Types:</span>
                <span style={{color:'var(--text-secondary)'}}>{attackTypes.join(' · ')}</span>
              </div>
            )}
            {feeds.length > 0 && (
              <div style={{display:'flex', alignItems:'center', gap:4, marginTop:3, fontSize:10}}>
                <span style={{color:'var(--text-muted)', fontWeight:600}}>Feeds:</span>
                <span style={{color:'var(--text-secondary)'}}>{feeds.join(', ')}</span>
              </div>
            )}
          </div>

          {/* Data transparency + reporting guidance */}
          <div style={{fontSize:9, color:'var(--text-muted)', lineHeight:1.5, borderTop:'1px solid var(--border)', paddingTop:6, marginTop:4}}>
            <div style={{marginBottom:4}}>
              ⚠️ This location is statistically modeled — we only know the real attack types and source IPs from threat feeds.
            </div>
            <div style={{color:'var(--accent-yellow)', fontWeight:600}}>
              📋 To report a threat, use the <strong>Threat Intelligence</strong> panel (bottom-right of map) or <strong>Live Feed</strong> tab for source-based intelligence.
            </div>
          </div>
        </div>
      </Popup>
    </CircleMarker>
  );
}

// ==================== Helper: create SVG element ====================

function svgEl(tag: string, attrs?: Record<string, string>): SVGElement {
  const el = document.createElementNS(SVG_NS, tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      el.setAttribute(k, v);
    }
  }
  return el;
}

// ==================== Cached element refs for animation ====================

interface VectorElements {
  path: SVGLineElement;
  dot: SVGCircleElement;
  sourceDot: SVGCircleElement;
}

// ==================== Thread-safe shallow compare for vector lists ====================

function vectorsEqual(a: VectorLike[], b: VectorLike[]) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i].id !== b[i].id) return false;
  }
  return true;
}

// ==================== Animated SVG Attack Vectors (Performance Optimized) ====================

function AnimatedAttackOverlay({ vectors, visible }: { vectors: VectorLike[]; visible: boolean }) {
  const map = useMap();
  const svgRef = useRef<SVGSVGElement | null>(null);
  const overlayRef = useRef<L.SVGOverlay | null>(null);
  const animRef = useRef<number>(0);
  const startTimeRef = useRef<number>(0);
  const lastFrameTimeRef = useRef<number>(0);
  const elemCacheRef = useRef<Map<string, VectorElements>>(new Map());
  const lastVectorsRef = useRef<VectorLike[]>([]);
  const initializedRef = useRef(false);

  // Track tab visibility
  useEffect(() => {
    const handleVisibility = () => {
      if (document.hidden) {
        // Tab hidden — cancel animation to save CPU
        if (animRef.current) {
          cancelAnimationFrame(animRef.current);
          animRef.current = 0;
        }
      } else {
        // Tab visible again — restart animation from current time
        startTimeRef.current = performance.now() - (lastFrameTimeRef.current || 0);
        if (overlayRef.current && svgRef.current) {
          animRef.current = requestAnimationFrame(animate);
        }
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Build or rebuild SVG when vectors change
  useEffect(() => {
    if (!visible || vectors.length === 0) {
      if (overlayRef.current) {
        map.removeLayer(overlayRef.current);
        overlayRef.current = null;
        svgRef.current = null;
        elemCacheRef.current.clear();
        initializedRef.current = false;
      }
      return;
    }

    // Only rebuild if vectors actually changed (shallow compare by id)
    if (initializedRef.current && vectorsEqual(vectors, lastVectorsRef.current)) {
      // Still need to update the reference for the animate loop
      lastVectorsRef.current = vectors;
      return;
    }

    // Cleanup previous overlay
    if (overlayRef.current) {
      cancelAnimationFrame(animRef.current);
      map.removeLayer(overlayRef.current);
      overlayRef.current = null;
      svgRef.current = null;
      elemCacheRef.current.clear();
    }

    lastVectorsRef.current = vectors;

    // Create SVG element
    const svg = svgEl('svg', { class: 'attack-svg-overlay' }) as SVGSVGElement;
    svg.style.pointerEvents = 'none';
    svgRef.current = svg;

    // Create SVG defs with a single shared glow filter
    const defs = svgEl('defs');

    // Single glow filter
    const glowFilter = svgEl('filter', { id: 'attackGlow', x: '-50%', y: '-50%', width: '200%', height: '200%' });
    glowFilter.appendChild(svgEl('feGaussianBlur', { stdDeviation: '3', result: 'blur' }));
    const merge = svgEl('feMerge');
    merge.appendChild(svgEl('feMergeNode', { in: 'blur' }));
    merge.appendChild(svgEl('feMergeNode', { in: 'SourceGraphic' }));
    glowFilter.appendChild(merge);
    defs.appendChild(glowFilter);
    svg.appendChild(defs);

    // Create SVG groups for each attack vector — simplified for performance
    vectors.forEach((av) => {
      const color = riskColors[av.severity as RiskLevel] || riskColors.medium;
      const isCritical = av.severity === 'critical';
      const group = svgEl('g', { class: `attack-vector av-${av.id}` });

      // 1. Dashed path (subtle)
      const path = svgEl('line', {
        stroke: color,
        'stroke-width': isCritical ? '1.5' : '1',
        'stroke-opacity': isCritical ? '0.45' : '0.25',
        'stroke-dasharray': '6 5',
        class: 'attack-path',
      }) as SVGLineElement;
      group.appendChild(path);

      // 2. Main traveling dot
      const dot = svgEl('circle', {
        r: isCritical ? '4' : '3',
        fill: color,
        filter: 'url(#attackGlow)',
        class: 'attack-dot',
      }) as SVGCircleElement;
      group.appendChild(dot);

      // 3. Source dot (stationary)
      const sourceDot = svgEl('circle', {
        r: '3',
        fill: color,
        'fill-opacity': '0.5',
        filter: 'url(#attackGlow)',
        class: 'source-dot',
      }) as SVGCircleElement;
      group.appendChild(sourceDot);

      elemCacheRef.current.set(av.id, { path, dot, sourceDot });
      svg.appendChild(group);
    });

    // Create Leaflet SVGOverlay
    const bounds = map.getBounds();
    const overlay = L.svgOverlay(svg, bounds, {
      interactive: false,
      zIndex: 800,
    });
    overlay.addTo(map);
    overlayRef.current = overlay;

    // Listen for map moves to update bounds — instead of recalculating every frame
    const handleMoveEnd = () => {
      const els = svgRef.current;
      if (!els) return;
      const newBounds = map.getBounds();
      overlayRef.current?.setBounds(newBounds);
    };
    map.on('moveend zoomend', handleMoveEnd);

    startTimeRef.current = performance.now();
    lastFrameTimeRef.current = 0;
    initializedRef.current = true;

    // Start animation
    animRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animRef.current);
      map.off('moveend zoomend', handleMoveEnd);
      if (overlayRef.current) {
        map.removeLayer(overlayRef.current);
        overlayRef.current = null;
        svgRef.current = null;
        elemCacheRef.current.clear();
        initializedRef.current = false;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, visible, vectors]);

  // Animation loop — 10fps throttle (was 30fps), pauses when tab hidden
  const animate = useCallback((now: number) => {
    if (!svgRef.current || !overlayRef.current) return;

    // 10fps throttle: skip if less than 100ms since last frame (was 33ms)
    if (lastFrameTimeRef.current && now - lastFrameTimeRef.current < 100) {
      animRef.current = requestAnimationFrame(animate);
      return;
    }
    lastFrameTimeRef.current = now;

    // Pause if tab is hidden
    if (document.hidden) {
      animRef.current = requestAnimationFrame(animate);
      return;
    }

    const elapsed = (now - startTimeRef.current) / 1000;

    const vectorsArray = lastVectorsRef.current;
    const cache = elemCacheRef.current;

    // Batch update: minimize attribute calls per vector
    for (let i = 0; i < vectorsArray.length; i++) {
      const av = vectorsArray[i];
      const els = cache.get(av.id);
      if (!els) continue;

      const fromPoint = map.latLngToContainerPoint([av.fromLat, av.fromLng]);
      const toPoint = map.latLngToContainerPoint([av.toLat, av.toLng]);

      const x1 = fromPoint.x;
      const y1 = fromPoint.y;
      const x2 = toPoint.x;
      const y2 = toPoint.y;

      const cycleTime = av.severity === 'critical' ? 5 : 7;  // Slower cycle (was 4/5.5)
      const rawProgress = (elapsed / cycleTime) % 1;
      const progress = rawProgress < 0.5
        ? 2 * rawProgress * rawProgress
        : 1 - Math.pow(-2 * rawProgress + 2, 2) / 2;

      // Update path (set both x,y in one call via commas instead of separate calls)
      els.path.setAttribute('x1', String(x1));
      els.path.setAttribute('y1', String(y1));
      els.path.setAttribute('x2', String(x2));
      els.path.setAttribute('y2', String(y2));

      // Traveling dot position
      const dotX = x1 + (x2 - x1) * progress;
      const dotY = y1 + (y2 - y1) * progress;
      els.dot.setAttribute('cx', String(dotX));
      els.dot.setAttribute('cy', String(dotY));

      // Source dot only (remove ghost trail pulse to reduce SVG mutations)
      els.sourceDot.setAttribute('cx', String(x1));
      els.sourceDot.setAttribute('cy', String(y1));
    }

    animRef.current = requestAnimationFrame(animate);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}

// ==================== Crime Heatmap Overlay (GeoJSON State Boundaries) ====================

function CrimeHeatmap({ visible, crimeData }: { visible: boolean; crimeData: CrimeDataPoint[] }) {
  const crimeDataByName = React.useMemo(
    () => new Map(crimeData.map(cd => [cd.state.toLowerCase(), cd])),
    [crimeData]
  );

  if (!visible) return null;

  const maxCount = Math.max(...crimeData.map(cd => cd.incidentCount), 1);

  const geoStyle = (feature?: GeoJSON.Feature) => {
    const stateName = feature?.properties?.name?.toLowerCase();
    const cd = stateName ? crimeDataByName.get(stateName) : undefined;
    const intensity = cd ? Math.min(cd.incidentCount / maxCount, 1) : 0;
    const isHigh = intensity > 0.4;
    const isMedium = intensity > 0.1;

    const fillColor = isHigh ? '#ef4444' : isMedium ? '#eab308' : '#22c55e';
    const fillOpacity = cd ? 0.2 + intensity * 0.25 : 0.04;
    const color = cd ? (isHigh ? '#ef4444' : isMedium ? '#eab308' : '#22c55e') : '#3a4050';
    const weight = cd ? 1.5 : 0.5;
    const opacity = cd ? 0.5 : 0.15;

    return { color, weight, opacity, fillColor, fillOpacity };
  };

  const onEachFeature = (feature: GeoJSON.Feature, layer: L.Layer) => {
    const pathLayer = layer as L.Path;
    const stateName = feature?.properties?.name || 'Unknown State';
    const cd = crimeDataByName.get(stateName.toLowerCase());
    const intensity = cd ? Math.min(cd.incidentCount / maxCount, 1) : 0;
    const isHigh = intensity > 0.4;
    const isMedium = intensity > 0.1;
    const baseColor = isHigh ? '#ef4444' : isMedium ? '#eab308' : '#22c55e';

    pathLayer.bindTooltip(
      `<div style="text-align:center;font-family:Inter,sans-serif">
        <div style="font-weight:600;font-size:12px;margin-bottom:3px">${stateName}</div>
        ${cd ? `<div style="font-size:14px;font-weight:700;color:${baseColor}">${cd.incidentCount.toLocaleString()} incidents</div>
        <div style="font-size:10px;color:#94a3b8;margin-top:2px">NCRB 2022</div>` : '<div style="font-size:11px;color:#64748b">No crime data</div>'}
      </div>`,
      { sticky: true, className: 'state-tooltip' }
    );

    if (cd) {
      pathLayer.bindPopup(
        `<div style="text-align:center;font-family:Inter,sans-serif;min-width:160px">
          <h3 style="margin:0 0 6px;font-size:14px">${stateName}</h3>
          <div style="font-size:20px;font-weight:700;color:${baseColor};margin:4px 0">${cd.incidentCount.toLocaleString()}</div>
          <div style="font-size:11px;color:#94a3b8;margin-bottom:6px">cyber incidents (NCRB 2022)</div>
          <span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;
            background:${riskColors[cd.risk]}22;color:${riskColors[cd.risk]};border:1px solid ${riskColors[cd.risk]}">
            ${cd.risk.toUpperCase()} RISK
          </span>
        </div>`
      );
    }

    const originalStyle = geoStyle(feature);
    pathLayer.on('mouseover', function (this: L.Path) {
      this.setStyle({ weight: 2.5, fillOpacity: 0.4 });
      this.bringToFront();
    });
    pathLayer.on('mouseout', function (this: L.Path) {
      this.setStyle(originalStyle);
    });
  };

  return (
    <GeoJSON
      key="crime-heatmap"
      data={indiaStatesGeoJSON}
      style={geoStyle}
      onEachFeature={onEachFeature}
    />
  );
}

// ==================== Map Controller ====================

function MapController({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  const centerKey = `${center[0].toFixed(4)},${center[1].toFixed(4)}`;
  useEffect(() => {
    map.setView(center, zoom, { animate: true, duration: 0.8 });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [centerKey, zoom, map]);
  return null;
}

// ==================== Live Attack Counter (Compact, with LIVE badge) ====================

function AttackCounter({ vectors, visible, isConnected }: { vectors: VectorLike[]; visible: boolean; isConnected?: boolean }) {
  if (!visible || vectors.length === 0) return null;

  const criticalCount = vectors.filter(v => v.severity === 'critical').length;
  const mediumCount = vectors.filter(v => v.severity === 'medium').length;
  const totalCount = vectors.length;

  return (
    <div className="attack-counter">
      <div className="attack-counter-header">
        <span className="attack-counter-dot" />
        <span className="attack-counter-label">LIVE ATTACKS</span>
        <span className="attack-counter-value">{totalCount}</span>
        {isConnected && (
          <span className="attack-counter-live">
            <span className="live-dot-inline" /> LIVE
          </span>
        )}
      </div>
      <div className="attack-counter-stats">
        <span className="attack-critical">{criticalCount} critical</span>
        <span className="attack-sep">·</span>
        <span className="attack-medium">{mediumCount} medium</span>
      </div>
    </div>
  );
}

// ==================== Origin Intelligence Summary ====================

function OriginSummary({ vectors }: { vectors: VectorLike[] }) {
  // Group by origin country
  const originMap = new Map<string, { count: number; attacks: string[]; severity: string }>();
  vectors.forEach(v => {
    const existing = originMap.get(v.from);
    if (existing) {
      existing.count++;
      if (!existing.attacks.includes(v.attackType)) existing.attacks.push(v.attackType);
      if (v.severity === 'critical') existing.severity = 'critical';
      else if (v.severity === 'medium' && existing.severity !== 'critical') existing.severity = 'medium';
    } else {
      originMap.set(v.from, { count: 1, attacks: [v.attackType], severity: v.severity });
    }
  });

  const origins = Array.from(originMap.entries());

  return (
    <div className="origin-summary">
      <div className="origin-summary-title">ORIGIN INTELLIGENCE</div>
      <div className="origin-list">
        {origins.map(([country, data]) => (
          <div key={country} className={`origin-item ${data.severity}`}>
            <span className="origin-flag">{COUNTRY_FLAGS[country] || '🏴'}</span>
            <span className="origin-country">{country}</span>
            <span className="origin-count">{data.count}</span>
            <span className="origin-attacks">{data.attacks.slice(0, 2).join(', ')}{data.attacks.length > 2 ? '...' : ''}</span>
          </div>
        ))}
      </div>
    </div>
  );
}



// ==================== Attack Vector Table (Detailed) ====================

function AttackVectorTable({ vectors, onSelect }: { vectors: VectorLike[]; onSelect?: (v: VectorLike) => void }) {
  return (
    <div className="av-table">
      <div className="av-table-header">
        <span className="av-col-source" style={{flex:'0 0 18px'}} />
        <span className="av-col-origin">Origin</span>
        <span className="av-col-target">Target</span>
        <span className="av-col-type">Type</span>
        <span className="av-col-severity">Severity</span>
      </div>
      {vectors.map(av => {
        const feedColor = FEED_COLORS[av.source || ''] || '#5a6a80';
        const feedLabel = FEED_LABELS[av.source || ''] || '?';
        return (
          <div key={av.id} className={`av-row ${av.severity}`} onClick={() => onSelect?.(av)} title={`Click for details — Source: ${av.source || 'Unknown'}`}>
            <span className="av-col-source" style={{flex:'0 0 18px', display:'flex', justifyContent:'center'}}>
              <span className="feed-source-dot" style={{ background: feedColor }} title={`Source: ${av.source || 'Unknown'}`} />
            </span>
            <span className="av-col-origin">{COUNTRY_FLAGS[av.from] || '🏴'} {av.from}</span>
            <span className="av-col-target">→ {av.to}</span>
            <span className="av-col-type">{av.attackType}</span>
            <span className="av-col-severity">
              <span className={`severity-badge ${av.severity}`}>{av.severity}</span>
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ==================== Attack Info Panel (Enhanced — Rich Origin Intelligence) ====================

function AttackInfoPanel({ vectors, visible, onSelectVector }: { vectors: VectorLike[]; visible: boolean; onSelectVector?: (v: VectorLike) => void }) {
  const [panelOpen, setPanelOpen] = useState(false); // collapsed to a floating button by default, like the AI chat assistant
  const [isOpen, setIsOpen] = useState(true); // internal accordion for the body sections, once the panel itself is open
  if (!visible || vectors.length === 0) return null;

  const criticalCount = vectors.filter(v => v.severity === 'critical').length;
  const mediumCount = vectors.filter(v => v.severity === 'medium').length;
  const safeCount = vectors.filter(v => v.severity === 'safe').length;
  const uniqueOrigins = new Set(vectors.map(v => v.from)).size;
  const uniqueTypes = new Set(vectors.map(v => v.attackType)).size;

  if (!panelOpen) {
    return (
      <button
        className="map-attack-info-fab"
        onClick={() => setPanelOpen(true)}
        title={`Threat Intelligence — ${vectors.length} active vectors`}
      >
        <ShieldIcon size={20} color="var(--accent-red)" />
        {criticalCount > 0 && <span className="map-attack-info-fab-badge">{criticalCount}</span>}
      </button>
    );
  }

  return (
    <div className="map-attack-info-panel">
      <div className="map-attack-info-header" onClick={() => setIsOpen(!isOpen)}>
        <div className="maih-left">
          <span className="maih-icon">🛡️</span>
          <div className="maih-text">
            <span className="maih-title">Threat Intelligence</span>
            <span className="maih-subtitle">{vectors.length} active vectors · {uniqueOrigins} origins · {uniqueTypes} attack types</span>
          </div>
        </div>
        <div className="maih-right">
          <div className="maih-severity-strip">
            {criticalCount > 0 && <span className="sev-strip-item critical">{criticalCount}</span>}
            {mediumCount > 0 && <span className="sev-strip-item medium">{mediumCount}</span>}
            {safeCount > 0 && <span className="sev-strip-item safe">{safeCount}</span>}
          </div>
          <span className={`maih-chevron ${isOpen ? 'open' : ''}`}>▼</span>
          <button
            className="maih-close-btn"
            onClick={(e) => { e.stopPropagation(); setPanelOpen(false); }}
            title="Minimize Threat Intelligence"
          >
            <CloseIcon size={13} />
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="map-attack-info-body">
          {/* Attack Type Distribution */}
          <div className="av-distribution">
            {criticalCount > 0 && (
              <div className="av-dist-item">
                <span className="av-dist-bar critical" style={{ width: `${(criticalCount / vectors.length) * 100}%` }} />
                <span className="av-dist-label">Critical {criticalCount}</span>
              </div>
            )}
            {mediumCount > 0 && (
              <div className="av-dist-item">
                <span className="av-dist-bar medium" style={{ width: `${(mediumCount / vectors.length) * 100}%` }} />
                <span className="av-dist-label">Medium {mediumCount}</span>
              </div>
            )}
            {safeCount > 0 && (
              <div className="av-dist-item">
                <span className="av-dist-bar safe" style={{ width: `${(safeCount / vectors.length) * 100}%` }} />
                <span className="av-dist-label">Low {safeCount}</span>
              </div>
            )}
          </div>

          {/* Origin Intelligence */}
          <OriginSummary vectors={vectors} />

          {/* Detailed Vector Table */}
          <div className="av-section-title">ATTACK ROUTES</div>
          <AttackVectorTable vectors={vectors} onSelect={onSelectVector} />
        </div>
      )}
    </div>
  );
}

// ==================== Main Map Component ====================

export default function IndiaMap() {
  const { state, dispatch } = useApp();
  const { state: threatState } = useThreatContext();
  const [showAttacks, setShowAttacks] = useState(true);
  const [selectedVector, setSelectedVector] = useState<VectorLike | null>(null);
  const [showDataSources, setShowDataSources] = useState(false);
  const [ncrbCrimeData, setNcrbCrimeData] = useState<CrimeDataPoint[] | null>(null);

  // Fetch real NCRB crime data from backend
  useEffect(() => {
    fetch('/api/crime-data')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data?.states) {
          setNcrbCrimeData(data.states);
        }
      })
      .catch(() => {
        // NCRB API not available — crime overlay will be empty
      });
  }, []);

  // Use only real attack vectors from WebSocket — show empty state when disconnected
  const activeAttackVectors = React.useMemo(() => 
    threatState.attackVectors,
    [threatState.attackVectors]
  );

  // Use real NCRB data from backend, empty array if unavailable
  const crimeData = React.useMemo(() =>
    ncrbCrimeData ?? ([] as CrimeDataPoint[]),
    [ncrbCrimeData]
  );

  const handleZoomToIndia = useCallback(() => {
    dispatch({ type: 'SET_MAP_CENTER', payload: [20.5937, 78.9629] });
    dispatch({ type: 'SET_MAP_ZOOM', payload: 5 });
    dispatch({ type: 'SET_SELECTED_CITY', payload: null });
  }, [dispatch]);

  return (
    <div className="map-container">
      <MapContainer
        center={state.mapCenter}
        zoom={state.mapZoom}
        className="map-wrapper"
        zoomControl={true}
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        <MapController center={state.mapCenter} zoom={state.mapZoom} />

        {/* Animated SVG attack vectors */}
        <AnimatedAttackOverlay vectors={activeAttackVectors} visible={showAttacks} />

        {/* Crime heatmap overlay — real NCRB 2022 data from backend */}
        <CrimeHeatmap visible={state.showCrimeOverlay} crimeData={crimeData} />

        {/* City markers — only shown when WebSocket provides real city data */}
        {threatState.cities.map(city => (
          <CityMarker key={city.name} city={city as CityData} />
        ))}

        {/* Destination pins — show approximated target cities for active attack vectors */}
        {showAttacks && (
          <DestinationPins vectors={activeAttackVectors} onSelectVector={setSelectedVector} />
        )}
      </MapContainer>

      {/* Connection status bar (top-center) */}
      <div className={`map-connection-status ${threatState.isConnected ? 'connected' : 'disconnected'}`}>
        <span className="mcs-dot" />
        <span className="mcs-text">
          {threatState.isConnected ? 'LIVE — Real threat data from ThreatFox, Feodo & IPsum' : 'Connecting to threat feed...'}
        </span>
        {threatState.isConnected && (
          <span className="mcs-badge">REAL DATA</span>
        )}
      </div>

      {/* Live attack counter (compact, top-right) */}
      <AttackCounter vectors={activeAttackVectors} visible={showAttacks} isConnected={threatState.isConnected} />

      {/* Attack info panel with origin intelligence (bottom-right, open by default) */}
      <AttackInfoPanel vectors={activeAttackVectors} visible={showAttacks} onSelectVector={setSelectedVector} />

      {/* Vector detail modal */}
      <VectorDetailModal vector={selectedVector} onClose={() => setSelectedVector(null)} />

      {/* Data Sources Health Panel */}
      <DataSourcesPanel isOpen={showDataSources} onClose={() => setShowDataSources(false)} />

      {/* Map Overlay Controls */}
      <div className="map-overlay-top">
        <button
          className={`map-control-btn ${showAttacks ? 'active' : ''}`}
          onClick={() => setShowAttacks(!showAttacks)}
        >
          <BoltIcon size={13} /> {showAttacks ? 'Hide' : 'Show'} Attacks
        </button>
        <button
          className={`map-control-btn ${state.showCrimeOverlay ? 'active' : ''}`}
          onClick={() => dispatch({ type: 'TOGGLE_CRIME_OVERLAY' })}
        >
          <FlameIcon size={13} /> Crime Data
        </button>
        <button
          className="map-control-btn"
          onClick={() => setShowDataSources(true)}
          title="View health status of all data sources"
        >
          <span style={{ fontSize:'13px' }}>📡</span> Data Sources
        </button>
        <button
          className={`map-control-btn ${state.showGraphView ? 'active' : ''}`}
          onClick={() => dispatch({ type: 'TOGGLE_GRAPH_VIEW' })}
        >
          <GraphIcon size={13} /> Graph View
        </button>
      </div>

      <div className="map-controls">
        <button className="map-control-btn" onClick={handleZoomToIndia}>
          <HomeIcon size={13} /> Reset View
        </button>
        {state.selectedCity && (
          <button
            className="map-control-btn"
            onClick={() => dispatch({ type: 'RUN_SEARCH', payload: state.selectedCity!.name })}
          >
          <SearchIcon size={13} /> Search {state.selectedCity.name}
          </button>
        )}
      </div>

      {/* Legend - bottom-left */}
      <div className="map-legend">
        <div className="legend-title">THREAT LEVEL</div>
        <div className="legend-item">
          <span className="legend-dot green" /> Safe
        </div>
        <div className="legend-item">
          <span className="legend-dot yellow" /> Medium Risk
        </div>
        <div className="legend-item">
          <span className="legend-dot red" /> Critical
        </div>
        <div className="legend-divider" />
        <div className="legend-item">
          <span className="legend-line dashed" /> Live Attack Vector
        </div>
        <div className="legend-item">
          <span className="legend-line dot" /> Traveling Packet
        </div>

        {/* Data Source Legend */}
        <div className="legend-divider" />
        <div className="legend-title">DATA SOURCES</div>
        <div className="legend-item">
          <span className="feed-legend-dot" style={{ background: '#8b5cf6' }} />
          ThreatFox (Malware IOCs)
        </div>
        <div className="legend-item">
          <span className="feed-legend-dot" style={{ background: '#06b6d4' }} />
          Feodo (C2 Servers)
        </div>
        <div className="legend-item">
          <span className="feed-legend-dot" style={{ background: '#5a6a80' }} />
          IPsum (Blacklist Score)
        </div>

        {state.showCrimeOverlay && (
          <>
            <div className="legend-divider" />
            <div className="legend-item">
              <span className="legend-dot gradient" /> NCRB Crime Data (2022)
            </div>
          </>
        )}
      </div>
    </div>
  );
}
