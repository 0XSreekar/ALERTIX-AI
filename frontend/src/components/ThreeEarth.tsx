import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";

function VolcanoCone() {
  const meshRef = useRef<THREE.Mesh>(null);
  useFrame((_s, delta) => {
    if (meshRef.current) meshRef.current.rotation.y += delta * 0.06;
  });
  return (
    <mesh ref={meshRef} position={[0, -1.2, 0]} castShadow>
      <coneGeometry args={[2.2, 3.2, 64, 1, true]} />
      <meshStandardMaterial
        color="#1a0a00"
        roughness={0.95}
        metalness={0.05}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

function LavaCrater() {
  const meshRef = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (meshRef.current) {
      const mat = meshRef.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 0.6 + Math.sin(clock.elapsedTime * 2.5) * 0.4;
    }
  });
  return (
    <mesh ref={meshRef} position={[0, 0.42, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <circleGeometry args={[0.52, 48]} />
      <meshStandardMaterial
        color="#ff2200"
        emissive="#ff4400"
        emissiveIntensity={0.8}
        roughness={0.3}
      />
    </mesh>
  );
}

function LavaGlow() {
  return (
    <mesh position={[0, 0.42, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <circleGeometry args={[1.1, 48]} />
      <meshBasicMaterial color="#ff3300" transparent opacity={0.12} />
    </mesh>
  );
}

function LavaStream({ angle, length }: { angle: number; length: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (meshRef.current) {
      const mat = meshRef.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 0.4 + Math.sin(clock.elapsedTime * 3 + angle) * 0.3;
      mat.opacity = 0.6 + Math.sin(clock.elapsedTime * 2 + angle) * 0.3;
    }
  });
  const x = Math.cos(angle) * (0.25 + length * 0.5);
  const z = Math.sin(angle) * (0.25 + length * 0.5);
  const slope = -Math.atan(1.45 / 2.2);
  return (
    <mesh ref={meshRef} position={[x, 0.3 - length * 0.5, z]} rotation={[slope, angle, 0]}>
      <planeGeometry args={[0.08, length * 0.9]} />
      <meshStandardMaterial
        color="#ff4400"
        emissive="#ff2200"
        emissiveIntensity={0.6}
        transparent
        opacity={0.8}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

function EruptionParticles() {
  const count = 180;
  const { positions, offsets } = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const off = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const r = Math.random() * 0.3;
      pos[i * 3] = Math.cos(theta) * r;
      pos[i * 3 + 1] = 0.42;
      pos[i * 3 + 2] = Math.sin(theta) * r;
      off[i] = Math.random() * Math.PI * 2;
    }
    return { positions: pos, offsets: off };
  }, []);

  const geoRef = useRef<THREE.BufferGeometry>(null);
  const posRef = useRef(positions.slice());

  useFrame(({ clock }) => {
    if (!geoRef.current) return;
    const t = clock.elapsedTime;
    const cur = posRef.current;
    for (let i = 0; i < count; i++) {
      const phase = ((t * 1.2 + offsets[i]) % (Math.PI * 2)) / (Math.PI * 2);
      const theta = offsets[i] * 7;
      const r = Math.random() * 0.25;
      cur[i * 3] = Math.cos(theta) * r + Math.sin(t + offsets[i]) * 0.05;
      cur[i * 3 + 1] = 0.42 + phase * 2.2 * (0.5 + offsets[i] * 0.3);
      cur[i * 3 + 2] = Math.sin(theta) * r + Math.cos(t + offsets[i]) * 0.05;
      // gravity pull
      cur[i * 3 + 1] -= phase * phase * 0.8;
    }
    geoRef.current.attributes.position.needsUpdate = true;
  });

  return (
    <points>
      <bufferGeometry ref={geoRef}>
        <bufferAttribute
          attach="attributes-position"
          array={posRef.current}
          count={count}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        color="#ff6600"
        size={0.055}
        transparent
        opacity={0.85}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

function AshCloud() {
  const count = 120;
  const { positions, offsets } = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const off = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const r = 0.3 + Math.random() * 1.8;
      pos[i * 3] = Math.cos(theta) * r * 0.6;
      pos[i * 3 + 1] = 0.8 + Math.random() * 2.2;
      pos[i * 3 + 2] = Math.sin(theta) * r * 0.6;
      off[i] = Math.random() * Math.PI * 2;
    }
    return { positions: pos, offsets: off };
  }, []);

  const geoRef = useRef<THREE.BufferGeometry>(null);
  const posRef = useRef(positions.slice());

  useFrame(({ clock }) => {
    if (!geoRef.current) return;
    const t = clock.elapsedTime * 0.18;
    for (let i = 0; i < count; i++) {
      posRef.current[i * 3] += Math.sin(t + offsets[i]) * 0.001;
      posRef.current[i * 3 + 1] += 0.0008;
      if (posRef.current[i * 3 + 1] > 3.5) posRef.current[i * 3 + 1] = 0.8;
    }
    geoRef.current.attributes.position.needsUpdate = true;
  });

  return (
    <points>
      <bufferGeometry ref={geoRef}>
        <bufferAttribute
          attach="attributes-position"
          array={posRef.current}
          count={count}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        color="#555555"
        size={0.09}
        transparent
        opacity={0.35}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}

function Ground() {
  return (
    <mesh position={[0, -2.8, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
      <circleGeometry args={[5, 64]} />
      <meshStandardMaterial color="#0d0500" roughness={1} metalness={0} />
    </mesh>
  );
}

const lavaAngles = [0, 0.9, 1.9, 3.0, 4.2, 5.4].map((a, i) => ({
  angle: a,
  length: 0.6 + i * 0.12,
}));

export default function ThreeEarth({ className = "h-[500px] w-full" }: { className?: string }) {
  return (
    <div className={className}>
      <Canvas
        camera={{ position: [0, 1.5, 6], fov: 42 }}
        shadows
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.08} />
        <pointLight position={[0, 0.42, 0]} color="#ff4400" intensity={6} distance={8} decay={2} />
        <pointLight position={[3, 4, 3]} color="#ff8800" intensity={1.5} />
        <pointLight position={[-3, 3, -2]} color="#220000" intensity={0.8} />

        <Ground />
        <VolcanoCone />
        {lavaAngles.map((l, i) => (
          <LavaStream key={i} angle={l.angle} length={l.length} />
        ))}
        <LavaGlow />
        <LavaCrater />
        <EruptionParticles />
        <AshCloud />

        <OrbitControls
          enableZoom={false}
          enablePan={false}
          autoRotate
          autoRotateSpeed={0.4}
          minPolarAngle={Math.PI / 4}
          maxPolarAngle={Math.PI / 2.2}
        />
      </Canvas>
    </div>
  );
}
