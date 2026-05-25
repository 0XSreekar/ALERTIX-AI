/**
 * Sentinel 3D globe — photorealistic Earth (NASA Blue Marble + bump + spec +
 * night lights), atmosphere shader, live event markers, forecast tracks +
 * halos, camera fly-to on selection.
 */
import { Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useLoader, useThree, type ThreeEvent } from "@react-three/fiber";
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
const KM_TO_RAD = 1 / 6371;

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

// ─── Real Earth ─────────────────────────────────────────────────────────────

function Earth() {
  const [colorMap, bumpMap, specMap, nightMap] = useLoader(THREE.TextureLoader, [
    "/textures/earth.jpg",
    "/textures/earth-topology.png",
    "/textures/water.png",
    "/textures/night.jpg",
  ]);

  // Improve colour quality
  useMemo(() => {
    [colorMap, nightMap].forEach((t) => {
      t.colorSpace = THREE.SRGBColorSpace;
      t.anisotropy = 8;
    });
  }, [colorMap, nightMap]);

  const earthRef = useRef<THREE.Mesh>(null);
  useFrame((_s, delta) => {
    if (earthRef.current) earthRef.current.rotation.y += delta * 0.015;
  });

  return (
    <group>
      <mesh ref={earthRef}>
        <sphereGeometry args={[RADIUS, 96, 96]} />
        <meshPhongMaterial
          map={colorMap}
          bumpMap={bumpMap}
          bumpScale={0.04}
          specularMap={specMap}
          specular={new THREE.Color("#3b82f6")}
          shininess={18}
          emissiveMap={nightMap}
          emissive={new THREE.Color("#fff6c2")}
          emissiveIntensity={0.45}
        />
      </mesh>
      {/* Atmosphere — inverted-normal halo */}
      <mesh>
        <sphereGeometry args={[RADIUS * 1.025, 64, 64]} />
        <shaderMaterial
          attach="material"
          transparent
          side={THREE.BackSide}
          uniforms={{ glowColor: { value: new THREE.Color("#3b82f6") } }}
          vertexShader={`
            varying vec3 vNormal;
            void main() {
              vNormal = normalize(normalMatrix * normal);
              gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
          `}
          fragmentShader={`
            varying vec3 vNormal;
            uniform vec3 glowColor;
            void main() {
              float intensity = pow(0.65 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.2);
              gl_FragColor = vec4(glowColor, 1.0) * intensity;
            }
          `}
        />
      </mesh>
    </group>
  );
}

// ─── India outline (subtle) ─────────────────────────────────────────────────

function IndiaBoundsRing() {
  const corners = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    const path: Array<[number, number]> = [
      [6, 68], [6, 98], [38, 98], [38, 68], [6, 68],
    ];
    for (let i = 0; i < path.length - 1; i++) {
      const [lat0, lon0] = path[i];
      const [lat1, lon1] = path[i + 1];
      const STEPS = 48;
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
      <lineBasicMaterial color="#22d3ee" transparent opacity={0.55} />
    </line>
  );
}

// ─── Event markers — tactical-contact style ────────────────────────────────
// Small filled centre + thin ring + pulse, oriented tangent to the globe.
// No giant translucent blobs.

interface EventPointProps {
  event: SentinelStreamEvent;
  selected: boolean;
  onSelect: () => void;
}

function EventPoint({ event, selected, onSelect }: EventPointProps) {
  const surfacePos = useMemo(
    () => new THREE.Vector3(...latLonToVec3(event.lat, event.lon, RADIUS * 1.005)),
    [event.lat, event.lon],
  );
  const dir = useMemo(() => surfacePos.clone().normalize(), [surfacePos]);

  // Quaternion to lay flat rings/discs onto the sphere surface
  const tangentQuat = useMemo(() => {
    const q = new THREE.Quaternion();
    q.setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
    return q;
  }, [dir]);

  const sev = severity(event);
  const color = HAZARD_COLOR[event.hazard_type] ?? "#fde047";
  const isDemo = event.source === "demo_seed";

  // SMALL, fixed-ish marker sizes — severity only nudges the outer ring
  const coreSize = selected ? 0.014 : 0.009;
  const ringInner = 0.015 + sev * 0.012;
  const ringOuter = ringInner + 0.004;
  const pulseMax = 0.04 + sev * 0.04;

  // Animated pulse — only the radius/opacity, not the marker itself
  const pulseRef = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!pulseRef.current) return;
    const t = (clock.elapsedTime * 0.8 + surfacePos.x) % 1;
    const scale = 1 + t * (pulseMax / ringOuter - 1);
    pulseRef.current.scale.set(scale, scale, scale);
    const mat = pulseRef.current.material as THREE.MeshBasicMaterial;
    mat.opacity = (1 - t) * 0.6 * (sev + 0.4);
  });

  return (
    <group position={surfacePos}>
      {/* Pulse ring (animated) */}
      <mesh ref={pulseRef} quaternion={tangentQuat}>
        <ringGeometry args={[ringOuter, ringOuter + 0.0015, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.6} side={THREE.DoubleSide} />
      </mesh>

      {/* Static outer ring */}
      <mesh quaternion={tangentQuat}>
        <ringGeometry args={[ringInner, ringOuter, 32]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={isDemo ? 0.65 : 0.95}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Filled centre dot — invisible click target also lives here */}
      <mesh
        quaternion={tangentQuat}
        onClick={(e: ThreeEvent<MouseEvent>) => {
          e.stopPropagation();
          onSelect();
        }}
        onPointerOver={(e: ThreeEvent<PointerEvent>) => {
          e.stopPropagation();
          (e.object as THREE.Mesh).scale.setScalar(1.3);
        }}
        onPointerOut={(e: ThreeEvent<PointerEvent>) => {
          (e.object as THREE.Mesh).scale.setScalar(1);
        }}
      >
        <circleGeometry args={[coreSize, 24]} />
        <meshBasicMaterial color={color} />
      </mesh>

      {/* Demo data dashed outer ring */}
      {isDemo && (
        <mesh quaternion={tangentQuat}>
          <ringGeometry args={[ringOuter + 0.004, ringOuter + 0.006, 24]} />
          <meshBasicMaterial
            color="#facc15"
            transparent
            opacity={0.85}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}

      {/* Selection crosshair */}
      {selected && (
        <>
          <mesh quaternion={tangentQuat}>
            <ringGeometry args={[ringOuter + 0.01, ringOuter + 0.012, 64]} />
            <meshBasicMaterial color="#ffffff" transparent opacity={0.9} side={THREE.DoubleSide} />
          </mesh>
          {/* Crosshair ticks */}
          {[0, 90, 180, 270].map((angle) => {
            const rad = (angle * Math.PI) / 180;
            const offset = ringOuter + 0.018;
            const tickLen = 0.008;
            const local = new THREE.Vector3(
              Math.cos(rad) * offset,
              Math.sin(rad) * offset,
              0,
            );
            local.applyQuaternion(tangentQuat);
            const local2 = new THREE.Vector3(
              Math.cos(rad) * (offset - tickLen),
              Math.sin(rad) * (offset - tickLen),
              0,
            );
            local2.applyQuaternion(tangentQuat);
            const geo = new THREE.BufferGeometry().setFromPoints([
              surfacePos.clone().add(local).sub(surfacePos),
              surfacePos.clone().add(local2).sub(surfacePos),
            ]);
            return (
              <line key={angle}>
                <primitive object={geo} attach="geometry" />
                <lineBasicMaterial color="#ffffff" transparent opacity={0.8} />
              </line>
            );
          })}
        </>
      )}
    </group>
  );
}

// ─── Cyclone forecast track ─────────────────────────────────────────────────

function CycloneTrack({ forecast }: { forecast: SentinelCycloneForecast }) {
  const points = useMemo(() => {
    const all = [forecast.current, ...forecast.track];
    return all.map((p) => new THREE.Vector3(...latLonToVec3(p.lat, p.lon, RADIUS * 1.015)));
  }, [forecast]);
  const geom = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points]);
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
        <lineBasicMaterial color="#a78bfa" linewidth={2} transparent opacity={0.85} />
      </line>
      {points.map((p, i) => (
        <mesh key={i} position={p}>
          <sphereGeometry args={[0.013, 8, 8]} />
          <meshBasicMaterial color="#a78bfa" transparent opacity={Math.max(0.2, 0.85 - i * 0.06)} />
        </mesh>
      ))}
      <mesh ref={headRef} position={headPos}>
        <sphereGeometry args={[0.045, 16, 16]} />
        <meshBasicMaterial color="#c4b5fd" transparent opacity={0.55} />
      </mesh>
    </group>
  );
}

// ─── Hazard halo ─────────────────────────────────────────────────────────────

function HazardHaloRing({ halo }: { halo: SentinelHazardHalo }) {
  const center = useMemo(
    () => new THREE.Vector3(...latLonToVec3(halo.lat, halo.lon, RADIUS * 1.005)),
    [halo],
  );
  const radius = halo.radius_km * KM_TO_RAD * RADIUS;
  const color = halo.hazard_type === "earthquake" ? "#fca5a5" : "#7dd3fc";
  const normal = useMemo(() => center.clone().normalize(), [center]);
  const quat = useMemo(() => {
    const q = new THREE.Quaternion();
    q.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
    return q;
  }, [normal]);
  return (
    <mesh position={center} quaternion={quat}>
      <ringGeometry args={[radius * 0.92, radius, 64]} />
      <meshBasicMaterial color={color} transparent opacity={0.5} side={THREE.DoubleSide} />
    </mesh>
  );
}

// ─── Camera fly-to ──────────────────────────────────────────────────────────

function CameraFlyTo({
  target,
  controls,
}: {
  target: [number, number, number] | null;
  controls: React.MutableRefObject<{ target: THREE.Vector3; update: () => void } | null>;
}) {
  const { camera } = useThree();
  const goal = useRef<THREE.Vector3 | null>(null);

  useEffect(() => {
    if (target) {
      const dir = new THREE.Vector3(...target).normalize();
      goal.current = dir.multiplyScalar(RADIUS * 2.0);
    } else {
      goal.current = null;
    }
  }, [target]);

  useFrame(() => {
    if (!goal.current) return;
    camera.position.lerp(goal.current, 0.06);
    if (controls.current) {
      controls.current.target.lerp(new THREE.Vector3(0, 0, 0), 0.08);
      controls.current.update();
    }
    if (camera.position.distanceTo(goal.current) < 0.03) goal.current = null;
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
  const indiaCam = useMemo(() => latLonToVec3(18, 82, RADIUS * 2.4), []);
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
      camera={{ position: indiaCam, fov: 38 }}
      onPointerMissed={() => onSelect(null)}
      gl={{ antialias: true }}
    >
      <color attach="background" args={["#020617"]} />
      <ambientLight intensity={0.25} />
      {/* Sun-like directional light from a fixed angle */}
      <directionalLight position={[8, 3, 5]} intensity={1.5} color="#fff8e1" />
      <pointLight position={[-5, -2, -4]} intensity={0.35} color="#3b82f6" />

      <Stars radius={50} depth={30} count={3000} factor={3} fade speed={0.4} />

      <Suspense fallback={null}>
        <Earth />
      </Suspense>
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
        minDistance={RADIUS * 1.3}
        maxDistance={RADIUS * 5}
        autoRotate={autoRotate && !flyTarget}
        autoRotateSpeed={0.3}
      />
    </Canvas>
  );
}
