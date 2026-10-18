"use client";

import { useEffect, useMemo, useState } from "react";
import HullView, { HullSurface } from "@/components/HullView";
import ParetoChart from "@/components/ParetoChart";
import SpeedChart from "@/components/SpeedChart";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8060";

type Requirements = {
  target_volume_m3: number;
  target_dwt_t: number;
  speed_kn: number;
  voyage_nm: number;
  enforce_panama: boolean;
  max_beam_m?: number | null;
  max_draft_m?: number | null;
  sea_margin: number;
};
type Project = {
  id: string;
  name: string;
  vessel_type: string;
  assumptions: Record<string, unknown>;
  requirements?: Requirements;
};
type Constraints = { ok: boolean; violations: string[]; warnings?: string[] };
type Candidate = {
  id: string;
  length_pp: number;
  beam: number;
  draft: number;
  block_coefficient: number;
  volume_m3: number;
  displacement_tonnes: number;
  demo_score: number;
  volume_gap: number;
  pareto: boolean;
  adopted: boolean;
  depth?: number;
  dwt_t?: number;
  lightweight_t?: number;
  froude?: number;
  power_index?: number;
  gm_indicator_m?: number;
  hold_volume_m3?: number;
  pd_kw?: number;
  rt_kn?: number;
  cargo_dwt_t?: number;
  fuel_t?: number;
  model_version?: string;
  mesh: number[][];
  surface?: HullSurface;
  resistance_curve?: { speed_kn: number; pd_kw: number; rt_kn: number }[];
};

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {hint ? <div className="kpi-hint">{hint}</div> : null}
    </div>
  );
}

function fmt(n: unknown, digits = 1) {
  if (n == null || n === "") return "—";
  const v = Number(n);
  return Number.isFinite(v) ? v.toLocaleString("ja-JP", { maximumFractionDigits: digits }) : "—";
}

export default function Page() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [pid, setPid] = useState("");
  const [hull, setHull] = useState({
    length_pp: 180,
    beam: 30,
    draft: 10,
    block_coefficient: 0.75,
    depth: 16,
    speed_kn: 14,
  });
  const [evalResult, setEvalResult] = useState<Record<string, unknown> | null>(null);
  const [cands, setCands] = useState<Candidate[]>([]);
  const [job, setJob] = useState("");
  const [jobStatus, setJobStatus] = useState("");
  const [sel, setSel] = useState<Candidate | null>(null);
  const [msg, setMsg] = useState("");
  const [filter, setFilter] = useState<"all" | "pareto" | "adopted" | "v3">("v3");
  const [req, setReq] = useState<Requirements>({
    target_volume_m3: 40000,
    target_dwt_t: 32000,
    speed_kn: 14,
    voyage_nm: 6000,
    enforce_panama: false,
    sea_margin: 0.15,
  });
  const [picked, setPicked] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [specText, setSpecText] = useState("Lpp 180 m、幅 30 m、喫水 10 m、型深 16 m、Cb 0.75、速力 14 kn の Handymax ばら積み。");
  const [llmText, setLlmText] = useState("");
  const [openaiOk, setOpenaiOk] = useState(false);

  async function loadProjects() {
    const r = await fetch(`${API}/api/projects`);
    const rows: Project[] = await r.json();
    setProjects(rows);
    if (!pid && rows[0]) setPid(rows[0].id);
    const h = await fetch(`${API}/health`).then((x) => x.json());
    setOpenaiOk(Boolean(h?.openai?.configured));
  }

  async function loadCands(id: string) {
    const r = await fetch(`${API}/api/projects/${id}/candidates`);
    setCands(await r.json());
  }

  useEffect(() => {
    loadProjects().catch(() => setMsg("API に接続できません"));
  }, []);

  useEffect(() => {
    if (pid) loadCands(pid).catch(() => undefined);
    const p = projects.find((x) => x.id === pid);
    if (p?.requirements) setReq({ ...req, ...p.requirements });
  }, [pid, projects]);

  const cons = evalResult?.constraints as Constraints | undefined;
  const surface = useMemo(() => {
    if (sel?.surface) return sel.surface;
    const s = evalResult?.surface;
    return s && typeof s === "object" ? (s as HullSurface) : null;
  }, [sel, evalResult]);
  const mesh = useMemo(() => {
    if (sel?.mesh?.length) return sel.mesh;
    const m = evalResult?.mesh;
    return Array.isArray(m) ? (m as number[][]) : [];
  }, [sel, evalResult]);

  const shown = cands.filter((c) => {
    if (filter === "pareto") return c.pareto;
    if (filter === "adopted") return c.adopted;
    if (filter === "v3") return c.model_version === "geom-v3";
    return true;
  });

  async function doEval() {
    setMsg("");
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/design/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...hull, check_bounds: true, requirements: req }),
      });
      const body = await r.json();
      setEvalResult(body);
      setSel(null);
    } finally {
      setBusy(false);
    }
  }

  async function doOpt() {
    setMsg("");
    setBusy(true);
    setJobStatus("queued");
    try {
      const r = await fetch(`${API}/api/optimization/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: pid, seed: 42, samples: 48, speed_kn: req.speed_kn }),
      });
      const body = await r.json();
      setJob(body.job_id);
      for (let i = 0; i < 80; i++) {
        await new Promise((x) => setTimeout(x, 400));
        const s = await fetch(`${API}/api/optimization/jobs/${body.job_id}`).then((x) => x.json());
        setJobStatus(s.status);
        if (s.status === "done" || s.status === "failed") {
          setMsg(`探索 ${s.status}（seed=${s.seed} / ${s.result_count ?? 0} 件 / ${s.model_version}）`);
          await loadCands(pid);
          return;
        }
      }
      setMsg("探索が時間内に終わりませんでした。候補一覧を再読込してください。");
    } finally {
      setBusy(false);
    }
  }

  async function doExtract() {
    setMsg("");
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/design/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: specText }),
      });
      const body = await r.json();
      if (!r.ok) {
        setMsg(body.detail ?? "仕様抽出に失敗しました");
        return;
      }
      if (body.hull) setHull({ ...hull, ...body.hull });
      if (body.evaluation) setEvalResult(body.evaluation);
      setSel(null);
      setLlmText(
        [
          body.note,
          body.extracted?.notes,
          body.missing?.length ? `未抽出: ${body.missing.join(", ")}` : "",
        ]
          .filter(Boolean)
          .join("\n"),
      );
    } finally {
      setBusy(false);
    }
  }

  async function doExplain() {
    setMsg("");
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/design/explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...hull, check_bounds: true }),
      });
      const body = await r.json();
      if (!r.ok) {
        setMsg(typeof body.detail === "string" ? body.detail : "説明生成に失敗しました");
        return;
      }
      setEvalResult(body.evaluation ?? evalResult);
      setLlmText(body.text ?? "");
    } finally {
      setBusy(false);
    }
  }

  async function saveReq() {
    if (!pid) return;
    const r = await fetch(`${API}/api/projects/${pid}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ requirements: req }),
    });
    if (r.ok) {
      setMsg("案件要件を保存しました");
      await loadProjects();
    }
  }

  async function doReport() {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/design/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...hull, check_bounds: true, requirements: req, project_id: pid || undefined }),
      });
      const body = await r.json();
      const blob = new Blob([body.markdown ?? ""], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "ship-design-report.md";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(false);
    }
  }

  function togglePick(id: string) {
    setPicked((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id].slice(-2)));
  }

  async function review(id: string, decision: "approved" | "rejected") {
    await fetch(`${API}/api/design/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: pid, candidate_id: id, decision, reviewer: "demo-designer" }),
    });
    await loadCands(pid);
  }

  function applyCandidate(c: Candidate) {
    setSel(c);
    setHull({
      length_pp: c.length_pp,
      beam: c.beam,
      draft: c.draft,
      block_coefficient: c.block_coefficient,
      depth: c.depth ?? 16,
      speed_kn: hull.speed_kn,
    });
  }

  const kpis = sel
    ? {
        volume: sel.volume_m3,
        disp: sel.displacement_tonnes,
        dwt: sel.dwt_t,
        cargo: sel.cargo_dwt_t,
        pd: sel.pd_kw,
        rt: sel.rt_kn,
        fuel: sel.fuel_t,
        fn: sel.froude,
      }
    : {
        volume: evalResult?.volume_m3,
        disp: evalResult?.displacement_tonnes,
        dwt: evalResult?.dwt_t,
        cargo: evalResult?.cargo_dwt_t,
        pd: evalResult?.pd_kw,
        rt: evalResult?.rt_kn,
        fuel: evalResult?.fuel_t,
        fn: evalResult?.froude,
      };
  const curve = (sel?.resistance_curve || evalResult?.resistance_curve) as
    | { speed_kn: number; pd_kw: number; rt_kn: number }[]
    | undefined;
  const pair = picked.map((id) => cands.find((c) => c.id === id)).filter(Boolean) as Candidate[];

  return (
    <>
      <div className="banner">
        教育用プロトタイプ（geom-v3）。排水容積は Lpp×B×T×Cb。Rt/Pd は Holtrop+ITTC
        の初期推定であり、試運転・復原性・船級ではありません。
      </div>
      <main className="wrap">
        <header className="head">
          <div>
            <h1 style={{ margin: 0, fontSize: 22 }}>船舶基本設計AI</h1>
            <p style={{ color: "var(--muted)", margin: "4px 0 0" }}>
              OPEN-01 Handymax ばら積み / 密度 1.025 t/m³ / 案件要件の ∇・DWT・航程を探索に使います
            </p>
          </div>
          <label>
            案件
            <select value={pid} onChange={(e) => setPid(e.target.value)}>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
        </header>

        <section className="kpis">
          <Kpi label="排水容積 ∇" value={`${fmt(kpis.volume, 0)} m³`} hint="Lpp×B×T×Cb" />
          <Kpi label="排水質量 Δ" value={`${fmt(kpis.disp, 0)} t`} hint="∇×1.025" />
          <Kpi label="教育用 DWT" value={`${fmt(kpis.dwt, 0)} t`} hint="Δ−LWT" />
          <Kpi label="貨物 DWT" value={`${fmt(kpis.cargo, 0)} t`} hint="燃料・消耗品控除後" />
          <Kpi label="初期推定 Rt" value={`${fmt(kpis.rt, 0)} kN`} hint="Holtrop。試運転ではない" />
          <Kpi label="初期推定 Pd" value={`${fmt(kpis.pd, 0)} kW`} hint="ηD=0.62・海余裕込み" />
          <Kpi label="燃料（航程）" value={`${fmt(kpis.fuel, 0)} t`} hint={`SFOC 180 g/kWh / ${req.voyage_nm} nm`} />
          <Kpi label="Fn" value={fmt(kpis.fn, 3)} hint="幾何指標" />
        </section>

        <section className="card">
          <h2 style={{ marginTop: 0, fontSize: 16 }}>案件要件</h2>
          <div className="row3">
            <label>
              目標 ∇ (m³)
              <input
                type="number"
                value={req.target_volume_m3}
                onChange={(e) => setReq({ ...req, target_volume_m3: Number(e.target.value) })}
              />
            </label>
            <label>
              目標 DWT (t)
              <input
                type="number"
                value={req.target_dwt_t}
                onChange={(e) => setReq({ ...req, target_dwt_t: Number(e.target.value) })}
              />
            </label>
            <label>
              設計速力 (kn)
              <input
                type="number"
                step="0.1"
                value={req.speed_kn}
                onChange={(e) => setReq({ ...req, speed_kn: Number(e.target.value) })}
              />
            </label>
            <label>
              航程 (nm)
              <input
                type="number"
                value={req.voyage_nm}
                onChange={(e) => setReq({ ...req, voyage_nm: Number(e.target.value) })}
              />
            </label>
            <label>
              喫水制限 (m)
              <input
                type="number"
                placeholder="なし"
                value={req.max_draft_m ?? ""}
                onChange={(e) => setReq({ ...req, max_draft_m: e.target.value ? Number(e.target.value) : null })}
              />
            </label>
            <label style={{ alignContent: "end" }}>
              <span>
                <input
                  type="checkbox"
                  checked={req.enforce_panama}
                  onChange={(e) => setReq({ ...req, enforce_panama: e.target.checked })}
                />{" "}
                旧パナマ閘門を制約にする
              </span>
            </label>
          </div>
          <div style={{ marginTop: 10 }}>
            <button className="secondary" onClick={saveReq} disabled={!pid || busy}>
              要件を保存
            </button>
          </div>
        </section>

        <div className="grid">
          <section className="card">
            <h2 style={{ marginTop: 0, fontSize: 16 }}>船型入力</h2>
            <div className="row3">
              {(
                [
                  ["length_pp", "Lpp (m)"],
                  ["beam", "B (m)"],
                  ["draft", "T (m)"],
                  ["depth", "D (m)"],
                  ["block_coefficient", "Cb"],
                  ["speed_kn", "Vs (kn)"],
                ] as const
              ).map(([k, lab]) => (
                <label key={k}>
                  {lab}
                  <input
                    type="number"
                    step="0.01"
                    value={hull[k]}
                    onChange={(e) => setHull({ ...hull, [k]: Number(e.target.value) })}
                  />
                </label>
              ))}
            </div>
            <label style={{ marginTop: 12 }}>
              仕様メモ（OpenAI で抽出。計算は geom-v3）
              <textarea
                rows={3}
                value={specText}
                onChange={(e) => setSpecText(e.target.value)}
              />
            </label>
            <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button onClick={doEval} disabled={busy}>
                評価
              </button>
              <button className="secondary" onClick={doExtract} disabled={busy || !openaiOk}>
                仕様を読み取る
              </button>
              <button className="secondary" onClick={doExplain} disabled={busy || !openaiOk}>
                評価を説明
              </button>
              <button className="secondary" onClick={doOpt} disabled={!pid || busy}>
                制約優先で探索
              </button>
              <button className="secondary" onClick={doReport} disabled={busy}>
                レポート
              </button>
            </div>
            <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 0 }}>
              {openaiOk ? "OPENAI_API_KEY を使用（抽出・説明のみ）" : "OpenAI 未設定。.env の OPENAI_API_KEY を確認してください"}
            </p>
            {cons && (
              <div className="chips">
                <span className={cons.ok ? "chip ok" : "chip bad"}>{cons.ok ? "制約通過" : "制約違反"}</span>
                {(cons.violations || []).map((x) => (
                  <span key={x} className="chip bad">
                    {x}
                  </span>
                ))}
                {(cons.warnings || []).map((x) => (
                  <span key={x} className="chip warn">
                    {x}
                  </span>
                ))}
              </div>
            )}
            {evalResult && (
              <p style={{ fontSize: 12, color: "var(--muted)" }}>
                L/B {fmt(evalResult.l_over_b, 2)} / B/T {fmt(evalResult.b_over_t, 2)} / L/D{" "}
                {fmt(evalResult.l_over_d, 2)} / Cp {fmt(evalResult.cp, 3)} / Cm {fmt(evalResult.cm, 3)} /
                濡れ面積 {fmt(evalResult.wetted_surface_m2, 0)} m² / 乾舷 {fmt(evalResult.freeboard_m, 1)} m
              </p>
            )}
            {llmText && <pre className="llm">{llmText}</pre>}
            {msg && <p>{msg}</p>}
            {job && (
              <p style={{ color: "var(--muted)" }}>
                job {job} {jobStatus && `（${jobStatus}）`}
              </p>
            )}
          </section>

          <section className="card">
            <h2 style={{ marginTop: 0, fontSize: 16 }}>3D（教育用シェル。線図ではない）</h2>
            <HullView mesh={mesh} surface={surface} />
            <p style={{ color: "var(--muted)", fontSize: 12 }}>水色は喫水線、黄はキール。回転表示。</p>
          </section>
        </div>

        <div className="grid">
          <section className="card">
            <h2 style={{ marginTop: 0, fontSize: 16 }}>候補分布（DWT↑ / パワー指標↓）</h2>
            <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 0 }}>
              緑が非支配（パレート）。実船最適ではありません。点をクリックして詳細を表示します。
            </p>
            <ParetoChart
              rows={cands}
              selected={sel?.id}
              onSelect={(id) => {
                const c = cands.find((x) => x.id === id);
                if (c) applyCandidate(c);
              }}
            />
            <h3 style={{ fontSize: 14, marginBottom: 4 }}>速力–Pd（初期推定）</h3>
            <SpeedChart points={curve} />
            {pair.length === 2 && (
              <p style={{ fontSize: 12, color: "var(--muted)" }}>
                比較 Δ（{pair[1].length_pp}m − {pair[0].length_pp}m）: ∇ {fmt((pair[1].volume_m3 || 0) - (pair[0].volume_m3 || 0), 0)} m³ /
                貨物 {fmt((Number(pair[1].cargo_dwt_t) || 0) - (Number(pair[0].cargo_dwt_t) || 0), 0)} t / Pd{" "}
                {fmt((Number(pair[1].pd_kw) || 0) - (Number(pair[0].pd_kw) || 0), 0)} kW
              </p>
            )}
          </section>
          <section className="card">
            <h2 style={{ marginTop: 0, fontSize: 16 }}>未評価（Skill 品質ゲート）</h2>
            <ul className="todo">
              <li>復原性（ Intact / 損傷 / IMO ）</li>
              <li>構造強度・船級規則</li>
              <li>抵抗・推進・プロペラ</li>
              <li>耐波性・操縦性</li>
              <li>CFD / 水槽試験との照合</li>
            </ul>
            <p style={{ color: "var(--muted)", fontSize: 12 }}>
              AI 推奨を正式設計に採用するには設計者と船級の確認が必要です。承認操作は教育用の記録です。
            </p>
          </section>
        </div>

        <section className="card">
          <div className="table-head">
            <h2 style={{ margin: 0, fontSize: 16 }}>候補（幾何＋教育用性能指標）</h2>
            <div className="filters">
              <button className={filter === "all" ? "" : "secondary"} onClick={() => setFilter("all")}>
                すべて
              </button>
              <button className={filter === "pareto" ? "" : "secondary"} onClick={() => setFilter("pareto")}>
                パレート
              </button>
              <button className={filter === "adopted" ? "" : "secondary"} onClick={() => setFilter("adopted")}>
                承認済
              </button>
              <button className={filter === "v3" ? "" : "secondary"} onClick={() => setFilter("v3")}>
                geom-v3
              </button>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>Pareto</th>
                  <th>Lpp</th>
                  <th>B</th>
                  <th>T</th>
                  <th>D</th>
                  <th>Cb</th>
                  <th>∇</th>
                  <th>貨物</th>
                  <th>Pd</th>
                  <th>版</th>
                  <th>承認</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => applyCandidate(c)}
                    style={{
                      cursor: "pointer",
                      background: sel?.id === c.id ? "#1d4ed855" : undefined,
                    }}
                  >
                    <td onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" checked={picked.includes(c.id)} onChange={() => togglePick(c.id)} />
                    </td>
                    <td>{c.pareto ? "●" : ""}</td>
                    <td>{c.length_pp}</td>
                    <td>{c.beam}</td>
                    <td>{c.draft}</td>
                    <td>{c.depth ?? "—"}</td>
                    <td>{c.block_coefficient}</td>
                    <td>{fmt(c.volume_m3, 0)}</td>
                    <td>{fmt(c.cargo_dwt_t, 0)}</td>
                    <td>{fmt(c.pd_kw, 0)}</td>
                    <td>{c.model_version ?? "—"}</td>
                    <td>
                      {c.adopted ? (
                        "承認済"
                      ) : (
                        <>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              review(c.id, "approved");
                            }}
                          >
                            承認
                          </button>{" "}
                          <button
                            className="secondary"
                            onClick={(e) => {
                              e.stopPropagation();
                              review(c.id, "rejected");
                            }}
                          >
                            差戻
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </>
  );
}
