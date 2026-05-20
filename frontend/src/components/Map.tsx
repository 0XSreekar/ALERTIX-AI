import { MapContainer, TileLayer, Marker, Popup, CircleMarker, useMap } from "react-leaflet";
import type { HazardEvent } from "@/lib/types";
import { HAZARD_COLORS, type HazardType } from "@/lib/types";
import "leaflet/dist/leaflet.css";

interface MapProps {
  events?: HazardEvent[];
  center?: [number, number];
  zoom?: number;
  className?: string;
  onEventClick?: (event: HazardEvent) => void;
}

function magnitudeToRadius(mag: number | null): number {
  if (!mag) return 4;
  if (mag < 3) return 4;
  if (mag < 5) return 6;
  if (mag < 6) return 10;
  if (mag < 7) return 14;
  return 20;
}

export default function Map({
  events = [],
  center = [20.5937, 78.9629], // India center
  zoom = 5,
  className = "h-[500px] w-full rounded-lg",
  onEventClick,
}: MapProps) {
  return (
    <MapContainer center={center} zoom={zoom} className={className} scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {events.map((event) => {
        if (!event.latitude || !event.longitude) return null;
        const color = HAZARD_COLORS[event.hazard_type as HazardType] || "#6b7280";
        return (
          <CircleMarker
            key={event.id}
            center={[event.latitude, event.longitude]}
            radius={magnitudeToRadius(event.magnitude)}
            pathOptions={{ color, fillColor: color, fillOpacity: 0.6, weight: 1 }}
            eventHandlers={{ click: () => onEventClick?.(event) }}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-semibold">
                  {event.hazard_type.toUpperCase()} — M{event.magnitude?.toFixed(1) ?? "?"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {event.metadata && typeof event.metadata === "object"
                    ? (event.metadata as Record<string, unknown>).place as string
                    : ""}
                </p>
                <p className="text-xs">
                  Depth: {event.depth_km?.toFixed(1) ?? "?"} km
                </p>
                <p className="text-xs text-muted-foreground">
                  {new Date(event.occurred_at).toLocaleString()}
                </p>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
