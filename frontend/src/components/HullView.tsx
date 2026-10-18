"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

export type HullSurface = {
  points: number[][];
  index?: number[];
  waterline?: number[][];
  keel?: number[][];
  stations?: number[][][];
};

function addLine(scene: THREE.Scene, pts: number[][], color: number, width = 1) {
  if (pts.length < 2) return;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pts.flat(), 3));
  scene.add(new THREE.Line(geo, new THREE.LineBasicMaterial({ color, linewidth: width })));
}

export default function HullView({
  mesh,
  surface,
}: {
  mesh: number[][];
  surface?: HullSurface | null;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1220);
    const camera = new THREE.PerspectiveCamera(45, el.clientWidth / 360, 0.1, 8000);
    camera.position.set(140, 110, 160);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(el.clientWidth, 360);
    el.innerHTML = "";
    el.appendChild(renderer.domElement);
    scene.add(new THREE.AmbientLight(0xffffff, 0.55));
    const dir = new THREE.DirectionalLight(0x9ec5ff, 0.95);
    dir.position.set(40, 80, 20);
    scene.add(dir);
    scene.add(new THREE.HemisphereLight(0x9ec5ff, 0x0b1220, 0.35));
    scene.add(new THREE.GridHelper(400, 20, 0x243044, 0x1a2436));

    const group = new THREE.Group();
    scene.add(group);

    const pts = surface?.points?.length ? surface.points : mesh;
    if (surface?.index?.length && pts.length) {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(pts.flat(), 3));
      geo.setIndex(surface.index);
      geo.computeVertexNormals();
      group.add(
        new THREE.Mesh(
          geo,
          new THREE.MeshPhongMaterial({
            color: 0x3b82f6,
            transparent: true,
            opacity: 0.42,
            side: THREE.DoubleSide,
            shininess: 40,
          }),
        ),
      );
    } else if (pts.length >= 8) {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(pts.flat(), 3));
      group.add(new THREE.Points(geo, new THREE.PointsMaterial({ color: 0x60a5fa, size: 2.0 })));
    }

    if (surface?.stations) {
      for (const st of surface.stations) {
        const port = st.filter((_, i) => i % 2 === 0);
        const stbd = st.filter((_, i) => i % 2 === 1);
        addLine(group, port, 0x64748b);
        addLine(group, stbd, 0x64748b);
      }
    }
    if (surface?.waterline?.length) {
      const port = surface.waterline.filter((_, i) => i % 2 === 0);
      const stbd = surface.waterline.filter((_, i) => i % 2 === 1);
      addLine(group, port, 0x38bdf8);
      addLine(group, stbd, 0x38bdf8);
    }
    if (surface?.keel) addLine(group, surface.keel, 0xfbbf24);

    const xs = pts.map((p) => p[0]);
    const mid = xs.length ? (Math.min(...xs) + Math.max(...xs)) / 2 : 0;
    camera.lookAt(mid, 0, 8);

    let raf = 0;
    const tick = () => {
      raf = requestAnimationFrame(tick);
      group.rotation.z += 0.003;
      renderer.render(scene, camera);
    };
    tick();
    return () => {
      cancelAnimationFrame(raf);
      renderer.dispose();
      el.innerHTML = "";
    };
  }, [mesh, surface]);

  return <div ref={ref} style={{ width: "100%", height: 360, borderRadius: 8, overflow: "hidden" }} />;
}
