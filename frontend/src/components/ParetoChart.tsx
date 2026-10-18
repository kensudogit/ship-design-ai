"use client";

type Pt = {
  id: string;
  dwt_t?: number | null;
  cargo_dwt_t?: number | null;
  power_index?: number | null;
  pd_kw?: number | null;
  pareto: boolean;
};

export default function ParetoChart({
  rows,
  selected,
  onSelect,
}: {
  rows: Pt[];
  selected?: string;
  onSelect: (id: string) => void;
}) {
  const pts = rows.filter((r) => (r.cargo_dwt_t ?? r.dwt_t) != null && (r.pd_kw ?? r.power_index) != null);
  if (pts.length < 2) {
    return <p style={{ color: "var(--muted)", fontSize: 12 }}>候補が少ないため分布を描けません。</p>;
  }
  const xs = pts.map((p) => Number(p.cargo_dwt_t ?? p.dwt_t));
  const ys = pts.map((p) => Number(p.pd_kw ?? p.power_index));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const w = 420;
  const h = 220;
  const pad = 36;
  const sx = (x: number) => pad + ((x - minX) / Math.max(maxX - minX, 1e-6)) * (w - pad * 2);
  const sy = (y: number) => h - pad - ((y - minY) / Math.max(maxY - minY, 1e-6)) * (h - pad * 2);

  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} role="img" aria-label="DWTとパワー指標の分布">
      <rect x="0" y="0" width={w} height={h} fill="#0f1728" rx="8" />
      <text x={w / 2} y={h - 8} textAnchor="middle" fill="#93a0b5" fontSize="11">
        教育用 貨物DWT (t) →
      </text>
      <text x="12" y="16" fill="#93a0b5" fontSize="11">
        パワー指標（実船馬力ではない）
      </text>
      {pts.map((p) => (
        <circle
          key={p.id}
          cx={sx(Number(p.cargo_dwt_t ?? p.dwt_t))}
          cy={sy(Number(p.pd_kw ?? p.power_index))}
          r={p.id === selected ? 7 : p.pareto ? 5 : 3.5}
          fill={p.id === selected ? "#fbbf24" : p.pareto ? "#34d399" : "#60a5fa"}
          opacity={p.pareto || p.id === selected ? 1 : 0.55}
          style={{ cursor: "pointer" }}
          onClick={() => onSelect(p.id)}
        />
      ))}
    </svg>
  );
}
