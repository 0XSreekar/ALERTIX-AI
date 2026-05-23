import { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "leaflet.markercluster";
import type { HazardEvent } from "@/lib/types";
import { HAZARD_COLORS, type HazardType } from "@/lib/types";

// All known hazard types with display labels
const HAZARD_TYPES: { type: HazardType; label: string; icon: string }[] = [
  { type: "earthquake", label: "Earthquakes", icon: "🔴" },
  { type: "flood", label: "Floods", icon: "🔵" },
  { type: "cyclone", label: "Cyclones", icon: "🟣" },
  { type: "wildfire", label: "Wildfires", icon: "🟠" },
  { type: "landslide", label: "Landslides", icon: "🟤" },
  { type: "damage", label: "Damage", icon: "⬜" },
];

function magnitudeToRadius(mag: number | null): number {
  if (!mag) return 4;
  if (mag < 3) return 4;
  if (mag < 5) return 6;
  if (mag < 6) return 10;
  if (mag < 7) return 14;
  return 20;
}

// ─── Cluster layer using imperative Leaflet API ──────────────────────────────

interface ClusterLayerProps {
  events: HazardEvent[];
  visibleTypes: Set<HazardType>;
  onEventClick?: (event: HazardEvent) => void;
}

function ClusterLayer({ events, visibleTypes, onEventClick }: ClusterLayerProps) {
  const map = useMap();
  const clusterRef = useRef<L.MarkerClusterGroup | null>(null);

  useEffect(() => {
    if (!clusterRef.current) {
      clusterRef.current = L.markerClusterGroup({ maxClusterRadius: 60, disableClusteringAtZoom: 8 });
      map.addLayer(clusterRef.current);
    }

    const cluster = clusterRef.current;
    cluster.clearLayers();

    events.forEach((event) => {
      if (!event.latitude || !event.longitude) return;
      if (!visibleTypes.has(event.hazard_type as HazardType)) return;

      const color = HAZARD_COLORS[event.hazard_type as HazardType] || "#6b7280";
      const radius = magnitudeToRadius(event.magnitude);

      const marker = L.circleMarker([event.latitude, event.longitude], {
        color,
        fillColor: color,
        fillOpacity: 0.6,
        weight: 1,
        radius,
      });

      const meta = event.metadata as Record<string, unknown> | null;
      marker.bindPopup(`
        <div style="font-size:13px">
          <strong>${event.hazard_type.toUpperCase()} — M${event.magnitude?.toFixed(1) ?? "?"}</strong><br/>
          <span style="color:#9ca3af">${meta?.place ?? ""}</span><br/>
          Depth: ${event.depth_km?.toFixed(1) ?? "?"} km<br/>
          <span style="color:#9ca3af">${new Date(event.occurred_at).toLocaleString()}</span>
        </div>
      `);

      if (onEventClick) {
        marker.on("click", () => onEventClick(event));
      }

      cluster.addLayer(marker);
    });

    return () => {
      cluster.clearLayers();
    };
  }, [events, visibleTypes, map, onEventClick]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (clusterRef.current) {
        map.removeLayer(clusterRef.current);
        clusterRef.current = null;
      }
    };
  }, [map]);

  return null;
}

// ─── Map Legend ──────────────────────────────────────────────────────────────

interface MapLegendProps {
  visibleTypes: Set<HazardType>;
  onToggle: (type: HazardType) => void;
}

function MapLegend({ visibleTypes, onToggle }: MapLegendProps) {
  return (
    <div className="absolute bottom-6 left-3 z-[1000] rounded-lg border border-border bg-background/90 p-3 shadow-lg backdrop-blur-sm">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Hazard Types
      </p>
      <div className="space-y-1">
        {HAZARD_TYPES.map(({ type, label, icon }) => {
          const color = HAZARD_COLORS[type];
          const active = visibleTypes.has(type);
          return (
            <button
              key={type}
              onClick={() => onToggle(type)}
              className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left text-xs transition-opacity ${
                active ? "opacity-100" : "opacity-40"
              }`}
            >
              <span
                className="inline-block h-3 w-3 flex-shrink-0 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span>
                {icon} {label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Layer Toggle Control (top-right) ────────────────────────────────────────

interface LayerToggleProps {
  visibleTypes: Set<HazardType>;
  onToggle: (type: HazardType) => void;
  onToggleAll: () => void;
}

function LayerToggle({ visibleTypes, onToggle, onToggleAll }: LayerToggleProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="absolute right-3 top-3 z-[1000]">
      <button
        onClick={() => setOpen((o) => !o)}
        className="rounded-lg border border-border bg-background/90 px-3 py-1.5 text-xs font-medium shadow backdrop-blur-sm"
      >
        Layers
      </button>
      {open && (
        <div className="mt-1 rounded-lg border border-border bg-background/95 p-3 shadow-lg backdrop-blur-sm">
          <div className="mb-2 flex items-center justify-between gap-4">
            <span className="text-xs font-semibold text-muted-foreground">Toggle Layers</span>
            <button onClick={onToggleAll} className="text-xs text-primary hover:underline">
              {visibleTypes.size === HAZARD_TYPES.length ? "Hide all" : "Show all"}
            </button>
          </div>
          <div className="space-y-1">
            {HAZARD_TYPES.map(({ type, label, icon }) => (
              <label key={type} className="flex cursor-pointer items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={visibleTypes.has(type)}
                  onChange={() => onToggle(type)}
                  className="rounded"
                />
                {icon} {label}
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Map ────────────────────────────────────────────────────────────────

interface MapProps {
  events?: HazardEvent[];
  center?: [number, number];
  zoom?: number;
  className?: string;
  onEventClick?: (event: HazardEvent) => void;
}

export default function Map({
  events = [],
  center = [20.5937, 78.9629], // India center
  zoom = 5,
  className = "h-[500px] w-full rounded-lg",
  onEventClick,
}: MapProps) {
  const [visibleTypes, setVisibleTypes] = useState<Set<HazardType>>(
    new Set(HAZARD_TYPES.map((h) => h.type)),
  );

  const toggleType = (type: HazardType) => {
    setVisibleTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const toggleAll = () => {
    setVisibleTypes((prev) =>
      prev.size === HAZARD_TYPES.length
        ? new Set()
        : new Set(HAZARD_TYPES.map((h) => h.type)),
    );
  };

  return (
    <div className={`relative ${className}`}>
      <MapContainer
        center={center}
        zoom={zoom}
        className="h-full w-full rounded-lg"
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ClusterLayer events={events} visibleTypes={visibleTypes} onEventClick={onEventClick} />
      </MapContainer>

      {/* Overlays rendered outside MapContainer so they aren't affected by Leaflet z-index */}
      <MapLegend visibleTypes={visibleTypes} onToggle={toggleType} />
      <LayerToggle visibleTypes={visibleTypes} onToggle={toggleType} onToggleAll={toggleAll} />
    </div>
  );
}
