/**
 * Sentinel 3D globe — earth sphere with live event particles plotted via
 * lat/lon → cartesian. Auto-rotates slowly, hover/click on a particle highlights
 * it and emits the event ID to the parent for the drill-down panel.
 */
import { useMemo, useRef, useState } from "react";
import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import * as THREE from "three";
import type { SentinelStreamEvent } from "@/lib/types";

const HAZARD_COLOR: Record<string, string> = {
  earthquake: "#ef4444",
  flood: "#38bdf8",
  cyclone: "#a78bfa",
  wildfire: "#f97316",
  landslide: "#92400e",
};

const RADIUS = 2;

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
    if (meshRef.current) meshRef.current.rotation.y += delta * 0.03;
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
      {/* Soft halo */}
      <mesh>
        <sphereGeometry args={[RADIUS * 1.04, 64, 64]} />
        <meshBasicMaterial
          color="#3b82f6"
          transparent
          opacity={0.07}
          side={THREE.BackSide}
        />
      </mesh>
    </group>
  );
}

// India bounding-box wireframe so users can see what we're focused on
function IndiaBoundsRing() {
  const corners = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    const path: Array<[number, number]> = [
      [6, 68], [6, 98], [38, 98], [38, 68], [6, 68],
    ];
    // Subdivide each edge for a smooth curve along the sphere
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
        onPointerOver={(e: ThreeEvent<PointerEvent>) => {
          e.stopPropagation();
          (e.object as THREE.Mesh).scale.multiplyScalar(1.3);
        }}
      >
        <sphereGeometry args={[size, 12, 12]} />
        <meshBasicMaterial color={color} transparent opacity={0.9} />
      </mesh>
      {/* Outer glow */}
      <mesh>
        <sphereGeometry args={[size * 2.6, 12, 12]} />
        <meshBasicMaterial color={color} transparent opacity={0.18} />
      </mesh>
      {/* Vertical beam for high-severity */}
      {sev > 0.5 && (
        <mesh
          position={[
            pos[0] === 0 ? 0 : pos[0] * 0.06,
            pos[1] === 0 ? 0 : pos[1] * 0.06,
            pos[2] === 0 ? 0 : pos[2] * 0.06,
          ]}
        >
          <cylinderGeometry args={[0.005, 0.02, 0.3 * sev, 8]} />
          <meshBasicMaterial color={color} transparent opacity={0.5} />
        </mesh>
      )}
    </group>
  );
}

interface GlobeProps {
  events: SentinelStreamEvent[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  autoRotate?: boolean;
}

export default function Globe({ events, selectedId, onSelect, autoRotate = true }: GlobeProps) {
  // Camera focuses on India (lat 22, lon 80) initially
  const indiaCam = useMemo(() => latLonToVec3(22, 80, RADIUS * 2.6), []);
  const [groupRotation] = useState<[number, number, number]>([0, 0, 0]);

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

      <group rotation={groupRotation}>
        <Earth />
        <IndiaBoundsRing />
        {events.map((e) => (
          <EventPoint
            key={e.id}
            event={e}
            selected={selectedId === e.id}
            onSelect={() => onSelect(e.id)}
          />
        ))}
      </group>

      <OrbitControls
        enablePan={false}
        minDistance={RADIUS * 1.4}
        maxDistance={RADIUS * 5}
        autoRotate={autoRotate}
        autoRotateSpeed={0.4}
      />
    </Canvas>
  );
}
