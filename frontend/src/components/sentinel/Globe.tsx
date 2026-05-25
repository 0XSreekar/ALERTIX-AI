/**
 * Sentinel 3D globe — earth sphere with live event particles, forecast cones,
 * and hazard halos. Camera flies to the selected event.
 */
import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import * as THREE from "three";
import type {
  SentinelCycloneForecast,
  SentinelHazardHalo,
  SentinelStreamEvent,
} from "@/lib/types";

const HAZARD_COLOR: Record<string, string> = {
  earthquake: "#ef4444",
  flood: "#38bdf8",
  cyclone: "#a78bfa",
  wildfire: "#f97316",
  landslide: "#92400e",
};

const RADIUS = 2;
const KM_TO_RAD = 1 / 6371; // 1 km in radians on a unit sphere

function latLonToVec3(lat: number, lon: number, r = RADIUS): [number, number, number] {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return [
    -(r * Math.sin(phi) * Math.cos(theta)),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.sin(theta),
  ];
}

function severity(e: SentinelStreamEvent): number {
  if (e.hazard_type === "earthquake") return Math.min(1, (e.mag ?? 0) / 7);
  if (e.hazard_type === "flood") return Math.min(1, (e.intensity ?? 0) / 4);
  if (e.hazard_type === "cyclone") {
    const w = Number((e.meta as { wind_kmh?: number })?.wind_kmh ?? 0);
    return Math.min(1, w / 220);
  }
  if (e.hazard_type === "wildfire") return Math.min(1, (e.intensity ?? 0) / 80);
  return 0.5;
}

function Earth() {
  const meshRef = useRef<THREE.Mesh>(null);
  useFrame((_s, delta) => {
    if (meshRef.current) meshRef.current.rotation.y += delta * 0.02;
  });
  return (
    <group>
      <mesh ref={meshRef}>
        <sphereGeometry args={[RADIUS, 96, 96]} />
        <meshPhongMaterial
          color="#0b1c2c"
          emissive="#08111a"
          emissiveIntensity={0.6}
          shininess={4}
          specular={new THREE.Color("#1f3a5f")}
        />
      </mesh>
      <mesh>
        <sphereGeometry args={[RADIUS * 1.04, 64, 64]} />
        <meshBasicMaterial color="#3b82f6" transparent opacity={0.07} side={THREE.BackSide} />
      </mesh>
    </group>
  );
}

function IndiaBoundsRing() {
  const corners = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    const path: Array<[number, number]> = [
      [6, 68], [6, 98], [38, 98], [38, 68], [6, 68],
    ];
    for (let i = 0; i < path.length - 1; i++) {
      const [lat0, lon0] = path[i];
      const [lat1, lon1] = path[i + 1];
      const STEPS = 32;
      for (let s = 0; s <= STEPS; s++) {
        const t = s / STEPS;
        const lat = lat0 + (lat1 - lat0) * t;
        const lon = lon0 + (lon1 - lon0) * t;
        pts.push(new THREE.Vector3(...latLonToVec3(lat, lon, RADIUS * 1.005)));
      }
    }
    return pts;
  }, []);
  const geom = useMemo(() => new THREE.BufferGeometry().setFromPoints(corners), [corners]);
  return (
    <line>
      <primitive object={geom} attach="geometry" />
      <lineBasicMaterial color="#22d3ee" transparent opacity={0.4} />
    </line>
  );
}

interface EventPointProps {
  event: SentinelStreamEvent;
  selected: boolean;
  onSelect: () => void;
}

function EventPoint({ event, selected, onSelect }: EventPointProps) {
  const pos = useMemo(
    () => latLonToVec3(event.lat, event.lon, RADIUS * 1.01),
    [event.lat, event.lon],
  );
  const sev = severity(event);
  const color = HAZARD_COLOR[event.hazard_type] ?? "#9ca3af";
  const size = 0.015 + sev * 0.05 + (selected ? 0.02 : 0);

  const meshRef = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = clock.elapsedTime * 1.8;
    const scale = 1 + Math.sin(t + pos[0]) * 0.15 * (sev + 0.4);
    meshRef.current.scale.setScalar(scale);
  });

  return (
    <group position={pos}>
      <mesh
        ref={meshRef}
        onClick={(e: ThreeEvent<MouseEvent>) => {
          e.stopPropagation();
          onSelect();
        }}
      >
        <sphereGeometry args={[size, 12, 12]} />
        <meshBasicMaterial color={color} transparent opacity={0.9} />
      </mesh>
      <mesh>
        <sphereGeometry args={[size * 2.6, 12, 12]} />
        <meshBasicMaterial color={color} transparent opacity={0.18} />
      </mesh>
      {sev > 0.5 && (
        <mesh
          position={[pos[0] * 0.06, pos[1] * 0.06, pos[2] * 0.06]}
        >
          <cylinderGeometry args={[0.005, 0.02, 0.3 * sev, 8]} />
          <meshBasicMaterial color={color} transparent opacity={0.5} />
        </mesh>
      )}
    </group>
  );
}

// ─── Forecast layers ─────────────────────────────────────────────────────────

function CycloneTrack({ forecast }: { forecast: SentinelCycloneForecast }) {
  const points = useMemo(() => {
    const all = [forecast.current, ...forecast.track];
    return all.map((p) => new THREE.Vector3(...latLonToVec3(p.lat, p.lon, RADIUS * 1.015)));
  }, [forecast]);
  const geom = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points]);
  // Pulsing head dot at the latest predicted position
  const headPos = points[points.length - 1] ?? points[0];
  const headRef = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (headRef.current) {
      const s = 1 + Math.sin(clock.elapsedTime * 3) * 0.25;
      headRef.current.scale.setScalar(s);
    }
  });
  return (
    <group>
      <line>
        <primitive object={geom} attach="geometry" />
        <lineBasicMaterial color="#a78bfa" linewidth={2} transparent opacity={0.75} />
      </line>
      {points.map((p, i) => (
        <mesh key={i} position={p}>
          <sphereGeometry args={[0.012, 8, 8]} />
          <meshBasicMaterial color="#a78bfa" transparent opacity={0.7 - i * 0.05} />
        </mesh>
      ))}
      <mesh ref={headRef} position={headPos}>
        <sphereGeometry args={[0.04, 16, 16]} />
        <meshBasicMaterial color="#c4b5fd" transparent opacity={0.45} />
      </mesh>
    </group>
  );
}

function HazardHaloRing({ halo }: { halo: SentinelHazardHalo }) {
  // Render as a flat ring tangent to the sphere
  const center = useMemo(
    () => new THREE.Vector3(...latLonToVec3(halo.lat, halo.lon, RADIUS * 1.005)),
    [halo],
  );
  const radius = halo.radius_km * KM_TO_RAD * RADIUS; // approx for small caps
  const color = halo.hazard_type === "earthquake" ? "#fca5a5" : "#7dd3fc";
  // Orient the ring's plane normal to point outward from globe centre
  const normal = useMemo(() => center.clone().normalize(), [center]);
  const quat = useMemo(() => {
    const q = new THREE.Quaternion();
    q.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
    return q;
  }, [normal]);
  return (
    <mesh position={center} quaternion={quat}>
      <ringGeometry args={[radius * 0.95, radius, 64]} />
      <meshBasicMaterial color={color} transparent opacity={0.35} side={THREE.DoubleSide} />
    </mesh>
  );
}

// ─── Camera fly-to ──────────────────────────────────────────────────────────

function CameraFlyTo({ target, controls }: {
  target: [number, number, number] | null;
  controls: React.MutableRefObject<{ target: THREE.Vector3; update: () => void } | null>;
}) {
  const { camera } = useThree();
  const goal = useRef<THREE.Vector3 | null>(null);

  useEffect(() => {
    if (target) {
      const dir = new THREE.Vector3(...target).normalize();
      goal.current = dir.multiplyScalar(RADIUS * 2.4);
    } else {
      goal.current = null;
    }
  }, [target]);

  useFrame(() => {
    if (!goal.current) return;
    camera.position.lerp(goal.current, 0.07);
    if (controls.current) {
      controls.current.target.lerp(new THREE.Vector3(0, 0, 0), 0.08);
      controls.current.update();
    }
    if (camera.position.distanceTo(goal.current) < 0.02) goal.current = null;
  });

  return null;
}

// ─── Main component ─────────────────────────────────────────────────────────

interface GlobeProps {
  events: SentinelStreamEvent[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  cyclones?: SentinelCycloneForecast[];
  halos?: SentinelHazardHalo[];
  autoRotate?: boolean;
}

export default function Globe({
  events,
  selectedId,
  onSelect,
  cyclones = [],
  halos = [],
  autoRotate = true,
}: GlobeProps) {
  const indiaCam = useMemo(() => latLonToVec3(22, 80, RADIUS * 2.6), []);
  const controlsRef = useRef<{ target: THREE.Vector3; update: () => void } | null>(null);

  const flyTarget = useMemo<[number, number, number] | null>(() => {
    if (!selectedId) return null;
    const e = events.find((ev) => ev.id === selectedId);
    if (!e) return null;
    return latLonToVec3(e.lat, e.lon, RADIUS);
  }, [selectedId, events]);

  return (
    <Canvas
      shadows
      camera={{ position: indiaCam, fov: 35 }}
      onPointerMissed={() => onSelect(null)}
    >
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 4, 6]} intensity={1.0} />
      <pointLight position={[-3, -2, -4]} intensity={0.4} color="#3b82f6" />

      <Stars radius={50} depth={30} count={2000} factor={3} fade speed={0.5} />

      <Earth />
      <IndiaBoundsRing />

      {halos.map((h) => (
        <HazardHaloRing key={h.event_id} halo={h} />
      ))}
      {cyclones.map((c) => (
        <CycloneTrack key={c.event_id} forecast={c} />
      ))}
      {events.map((e) => (
        <EventPoint
          key={e.id}
          event={e}
          selected={selectedId === e.id}
          onSelect={() => onSelect(e.id)}
        />
      ))}

      <CameraFlyTo target={flyTarget} controls={controlsRef} />
      <OrbitControls
        ref={controlsRef as unknown as React.Ref<never>}
        enablePan={false}
        minDistance={RADIUS * 1.4}
        maxDistance={RADIUS * 5}
        autoRotate={autoRotate && !flyTarget}
        autoRotateSpeed={0.4}
      />
    </Canvas>
  );
}
