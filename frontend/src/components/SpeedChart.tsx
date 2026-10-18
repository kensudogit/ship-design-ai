"use client";

type Pt = { speed_kn: number; pd_kw: number; rt_kn: number };

export default function SpeedChart({ points }: { points?: Pt[] | null }) {
  const pts = (points || []).filter((p) => p && p.speed_kn && p.pd_kw != null);
  if (pts.length < 2) {
    return <p style={{ color: "var(--muted)", fontSize: 12 }}>評価すると 10–16 kn の初期推定曲線が出ます。試運転ではありません。</p>;
  }
  const w = 420;
  const h = 220;
  const pad = 36;
  const xs = pts.map((p) => p.speed_kn);
  const ys = pts.map((p) => p.pd_kw);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = 0;
  const maxY = Math.max(...ys) * 1.08;
  const sx = (x: number) => pad + ((x - minX) / Math.max(maxX - minX, 1e-6)) * (w - pad * 2);
  const sy = (y: number) => h - pad - ((y - minY) / Math.max(maxY - minY, 1e-6)) * (h - pad * 2);
  const d = pts.map((p, i) => `${i ? "L" : "M"} ${sx(p.speed_kn)} ${sy(p.pd_kw)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} role="img" aria-label="初期推定の速力-Pd曲線">
      <rect x="0" y="0" width={w} height={h} fill="#0f1728" rx="8" />
      <path d={d} fill="none" stroke="#60a5fa" strokeWidth="2" />
      {pts.map((p) => (
        <circle key={p.speed_kn} cx={sx(p.speed_kn)} cy={sy(p.pd_kw)} r="3.5" fill="#93c5fd" />
      ))}
      <text x={w / 2} y={h - 8} textAnchor="middle" fill="#93a0b5" fontSize="11">
        Vs (kn) →
      </text>
      <text x="12" y="16" fill="#93a0b5" fontSize="11">
        初期推定 Pd (kW)。試運転ではない
      </text>
    </svg>
  );
}
