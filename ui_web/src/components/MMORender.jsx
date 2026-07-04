import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial, OrbitControls } from '@react-three/drei';

const QuantumShape = () => {
  const mesh = useRef();

  useFrame((state) => {
    if (!mesh.current) return;
    const elapsed = state.clock.getElapsedTime();
    mesh.current.rotation.x = elapsed * 0.2;
    mesh.current.rotation.y = elapsed * 0.3;
  });

  return (
    <Float speed={2} rotationIntensity={1} floatIntensity={1.4}>
      <mesh ref={mesh}>
        <icosahedronGeometry args={[1.45, 10]} />
        <MeshDistortMaterial
          color="#4f46e5"
          speed={4}
          distort={0.38}
          metalness={0.86}
          roughness={0.12}
          emissive="#312e81"
          emissiveIntensity={0.55}
        />
      </mesh>
    </Float>
  );
};

export const MMORender = () => (
  <Canvas camera={{ position: [0, 0, 5] }} className="h-full w-full bg-slate-950">
    <ambientLight intensity={0.5} />
    <pointLight position={[10, 10, 10]} intensity={1.5} />
    <spotLight position={[-10, 10, 10]} angle={0.15} penumbra={1} />
    <QuantumShape />
    <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={0.5} />
  </Canvas>
);
