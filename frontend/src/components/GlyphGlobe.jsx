import { useEffect, useRef } from "react";

export const GlyphGlobe = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let raf;
    let t = 0;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    const N = 480;
    const points = [];
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const phi = i * 2.399963;
      points.push({ x: Math.cos(phi) * r, y, z: Math.sin(phi) * r });
    }

    const draw = () => {
      const w = canvas.getBoundingClientRect().width;
      const h = canvas.getBoundingClientRect().height;
      ctx.clearRect(0, 0, w, h);
      const cx = w / 2;
      const cy = h / 2;
      const R = Math.min(w, h) * 0.33;

      t += 0.0032;
      const cosA = Math.cos(t);
      const sinA = Math.sin(t);
      const tilt = -0.42;
      const cosT = Math.cos(tilt);
      const sinT = Math.sin(tilt);

      const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 1.5);
      core.addColorStop(0, "rgba(16,185,129,0.28)");
      core.addColorStop(0.5, "rgba(6,182,212,0.08)");
      core.addColorStop(1, "rgba(8,11,17,0)");
      ctx.fillStyle = core;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.5, 0, Math.PI * 2);
      ctx.fill();

      const projected = points.map((p) => {
        let x = p.x * cosA - p.z * sinA;
        let z = p.x * sinA + p.z * cosA;
        let y = p.y;
        const y2 = y * cosT - z * sinT;
        const z2 = y * sinT + z * cosT;
        return { x, y: y2, z: z2 };
      });

      ctx.lineWidth = 1;
      for (let lat = -60; lat <= 60; lat += 30) {
        ctx.beginPath();
        const rad = (lat * Math.PI) / 180;
        for (let lon = 0; lon <= 360; lon += 6) {
          const lr = (lon * Math.PI) / 180;
          let x = Math.cos(rad) * Math.cos(lr);
          let z = Math.cos(rad) * Math.sin(lr);
          let y = Math.sin(rad);
          const rx = x * cosA - z * sinA;
          const rz = x * sinA + z * cosA;
          const y2 = y * cosT - rz * sinT;
          const z2 = y * sinT + rz * cosT;
          const sx = cx + rx * R;
          const sy = cy + y2 * R;
          const alpha = 0.12 + (z2 + 1) * 0.09;
          if (lon === 0) ctx.moveTo(sx, sy);
          else ctx.lineTo(sx, sy);
          ctx.strokeStyle = `rgba(6,182,212,${alpha})`;
        }
        ctx.stroke();
      }

      projected
        .sort((a, b) => a.z - b.z)
        .forEach((p) => {
          const sx = cx + p.x * R;
          const sy = cy + p.y * R;
          const depth = (p.z + 1) / 2;
          const size = 0.6 + depth * 1.9;
          const alpha = 0.15 + depth * 0.75;
          const front = p.z > 0.3;
          ctx.beginPath();
          ctx.arc(sx, sy, size, 0, Math.PI * 2);
          ctx.fillStyle = front
            ? `rgba(52,211,153,${alpha})`
            : `rgba(45,212,191,${alpha * 0.7})`;
          ctx.fill();
        });

      const op = projected[Math.floor((t * 40) % N)];
      if (op) {
        const sx = cx + op.x * R;
        const sy = cy + op.y * R;
        ctx.beginPath();
        ctx.arc(sx, sy, 3.2, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(245,158,11,0.95)";
        ctx.shadowColor = "rgba(245,158,11,0.8)";
        ctx.shadowBlur = 12;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      raf = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      data-testid="glyph-globe-canvas"
      className="block h-full w-full"
      aria-label="Animated glyph globe"
    />
  );
};
