import { useEffect, useRef } from "react";

// Cloud of micro-dots on a deforming sphere; `levelRef` (0..1) drives size and distortion.
export function VoiceOrb({ levelRef, active }: { levelRef: React.MutableRefObject<number>; active: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const activeRef = useRef(active);
  activeRef.current = active;

  useEffect(() => {
    const c = ref.current!;
    const ctx = c.getContext("2d")!;
    const N = 1400;
    const pts = Array.from({ length: N }, (_, i) => {
      const y = 1 - (i / (N - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const th = i * 2.399963;
      const roll = Math.random();
      const rgb = roll < 0.12 ? "255,255,255" : roll < 0.56 ? "0,200,255" : "198,255,0";
      return { x: Math.cos(th) * r, y, z: Math.sin(th) * r, j: Math.random(), rgb };
    });
    let raf = 0, t = 0, smooth = 0;
    const draw = () => {
      const dpr = window.devicePixelRatio || 1;
      const s = c.clientWidth;
      if (c.width !== Math.round(s * dpr)) c.width = c.height = Math.round(s * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, s, s);
      const target = activeRef.current ? levelRef.current : 0;
      smooth += (target - smooth) * 0.2;
      t += 0.008 + smooth * 0.04;
      const cx = s / 2, base = s * (0.3 + smooth * 0.08);
      const ca = Math.cos(t * 0.6), sa = Math.sin(t * 0.6), cb = Math.cos(0.4), sb = Math.sin(0.4);
      for (const p of pts) {
        const n =
          Math.sin(p.x * 3 + t * 2) * Math.cos(p.y * 4 - t * 1.5) +
          Math.sin(p.z * 5 + t * 2.4) * 0.5;
        const k = 1 + n * (0.12 + smooth * 0.45) + (p.j - 0.5) * (0.04 + smooth * 0.25);
        let x = p.x * k, y = p.y * k, z = p.z * k;
        const x1 = x * ca - z * sa; z = x * sa + z * ca; x = x1;
        const y1 = y * cb - z * sb; z = y * sb + z * cb; y = y1;
        const depth = (z + 1.4) / 2.8;
        ctx.fillStyle = `rgba(${p.rgb},${0.25 + depth * 0.75})`;
        const size = 0.6 + depth * 1.6;
        ctx.fillRect(cx + x * base - size / 2, cx + y * base - size / 2, size, size);
      }
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [levelRef]);

  return <canvas ref={ref} className="orb" aria-hidden />;
}
