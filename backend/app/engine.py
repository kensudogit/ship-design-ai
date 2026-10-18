"""教育用の初期設計評価。船級承認・実船抵抗・復原性認定ではない。"""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field

from app.resistance import estimate as estimate_resistance

MODEL_VERSION = "geom-v3"
SEAWATER_DENSITY_T_PER_M3 = 1.025
TARGET_VOLUME_M3 = 40_000.0
TARGET_DWT_T = 32_000.0
DESIGN_SPEED_KN = 14.0
G_M_S2 = 9.81
KN_TO_MS = 1852.0 / 3600.0
CM_DEFAULT = 0.98
DEPTH_DEFAULT = 16.0
PANAMA_LOCK_BEAM_M = 32.31

LPP_RANGE = (150.0, 220.0)
BEAM_RANGE = (25.0, 38.0)
DRAFT_RANGE = (8.0, 13.0)
CB_RANGE = (0.60, 0.85)
DEPTH_RANGE = (14.0, 20.0)
VOYAGE_NM_DEFAULT = 6000.0


@dataclass
class Requirements:
    target_volume_m3: float = TARGET_VOLUME_M3
    target_dwt_t: float = TARGET_DWT_T
    speed_kn: float = DESIGN_SPEED_KN
    voyage_nm: float = VOYAGE_NM_DEFAULT
    max_beam_m: float | None = None
    max_draft_m: float | None = None
    enforce_panama: bool = False
    sea_margin: float = 0.15

    @classmethod
    def from_dict(cls, data: dict | None) -> "Requirements":
        if not data:
            return cls()
        keys = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: data[k] for k in data if k in keys})

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Hull:
    length_pp: float
    beam: float
    draft: float
    block_coefficient: float
    prismatic_coefficient: float | None = None
    density: float = SEAWATER_DENSITY_T_PER_M3
    depth: float = DEPTH_DEFAULT
    speed_kn: float = DESIGN_SPEED_KN
    midship_coefficient: float | None = None

    def resolved_cm(self) -> float:
        if self.midship_coefficient is None:
            return CM_DEFAULT
        return self.midship_coefficient

    def resolved_cp(self) -> float:
        if self.prismatic_coefficient is not None:
            return self.prismatic_coefficient
        cm = self.resolved_cm()
        if cm <= 0:
            return self.block_coefficient
        return min(1.0, self.block_coefficient / cm)


@dataclass
class ConstraintResult:
    ok: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Evaluation:
    volume_m3: float
    displacement_tonnes: float
    lightweight_t: float
    dwt_t: float
    dwt_gap: float
    hold_volume_m3: float
    cp: float
    cm: float
    cwp: float
    l_over_b: float
    b_over_t: float
    l_over_d: float
    slenderness: float
    freeboard_m: float
    froude: float
    wetted_surface_m2: float
    gm_indicator_m: float
    power_index: float
    rt_kn: float
    pe_kw: float
    pd_kw: float
    fuel_t_per_day: float
    fuel_t: float
    cargo_dwt_t: float
    lcb_pct: float
    lwl_m: float
    form_factor: float
    resistance_curve: list[dict]
    demo_score: float
    volume_gap: float
    depth: float
    speed_kn: float
    voyage_nm: float
    constraints: ConstraintResult
    model_version: str = MODEL_VERSION
    density: float = SEAWATER_DENSITY_T_PER_M3
    note: str = (
        "educational preliminary estimate. not class-approved. "
        "not measured resistance. not IMO intact stability."
    )

    def payload(self) -> dict:
        data = asdict(self)
        data["constraints"] = asdict(self.constraints)
        return data


def _fn(h: Hull) -> float:
    if h.length_pp <= 0:
        return 0.0
    return (h.speed_kn * KN_TO_MS) / math.sqrt(G_M_S2 * h.length_pp)


def check_constraints(h: Hull, *, bounds: bool = False, req: Requirements | None = None) -> ConstraintResult:
    v: list[str] = []
    w: list[str] = []
    if min(h.length_pp, h.beam, h.draft, h.density, h.depth, h.speed_kn) <= 0:
        v.append("寸法・密度・速力は正であること")
    if not (0 < h.block_coefficient <= 1):
        v.append("Cb は (0, 1]")
    cm = h.resolved_cm()
    cp = h.resolved_cp()
    if not (0 < cm <= 1):
        v.append("Cm は (0, 1]")
    if not (0 < cp <= 1):
        v.append("Cp は (0, 1]")
    if h.block_coefficient > cm + 1e-9:
        v.append("Cb は Cm 以下（OPEN-13）")
    if h.prismatic_coefficient is not None and h.block_coefficient > cp + 1e-9:
        v.append("Cb は Cp 以下（OPEN-09）")
    if h.depth + 1e-9 < h.draft:
        v.append("型深 D は喫水 T 以上")
    if bounds:
        lo, hi = LPP_RANGE
        if not (lo <= h.length_pp <= hi):
            v.append(f"Lpp は {lo}–{hi} m（OPEN-05）")
        lo, hi = BEAM_RANGE
        if not (lo <= h.beam <= hi):
            v.append(f"B は {lo}–{hi} m（OPEN-05）")
        lo, hi = DRAFT_RANGE
        if not (lo <= h.draft <= hi):
            v.append(f"T は {lo}–{hi} m（OPEN-05）")
        lo, hi = CB_RANGE
        if not (lo <= h.block_coefficient <= hi):
            v.append(f"Cb は {lo}–{hi}（OPEN-05）")
        lo, hi = DEPTH_RANGE
        if not (lo <= h.depth <= hi):
            v.append(f"D は {lo}–{hi} m（OPEN-17）")
        lb = h.length_pp / h.beam if h.beam else 0
        if not (4.0 <= lb <= 9.0):
            v.append("L/B は教育用に 4–9")
        bt = h.beam / h.draft if h.draft else 0
        if not (2.0 <= bt <= 4.5):
            v.append("B/T は教育用に 2–4.5")
        if h.depth < h.draft + 3.0:
            v.append("乾舷は教育用に D−T ≥ 3 m（OPEN-15。IMO 乾舷ではない）")
        ld = h.length_pp / h.depth if h.depth else 0
        if not (9.0 <= ld <= 14.5):
            v.append("L/D は教育用に 9–14.5")
        fn = _fn(h)
        if not (0.12 <= fn <= 0.26):
            v.append("Fn は教育用に 0.12–0.26（OPEN-03 速力の幾何指標）")
        if h.beam > PANAMA_LOCK_BEAM_M:
            msg = f"B={h.beam:.2f} m は旧パナマ閘門 {PANAMA_LOCK_BEAM_M} m 超（OPEN-22）"
            if req and req.enforce_panama:
                v.append(msg + "。案件で閘門制限を有効化")
            else:
                w.append(msg + "。制限ではない")
        if req and req.max_beam_m and h.beam > req.max_beam_m + 1e-9:
            v.append(f"B が案件上限 {req.max_beam_m} m 超")
        if req and req.max_draft_m and h.draft > req.max_draft_m + 1e-9:
            v.append(f"T が案件喫水制限 {req.max_draft_m} m 超")
        if cm < 0.94:
            w.append("ばら積みの Cm は教育用に 0.94–0.995 が多い")
    return ConstraintResult(ok=not v, violations=v, warnings=w)


def evaluate(h: Hull, *, bounds: bool = False, req: Requirements | None = None) -> Evaluation:
    req = req or Requirements()
    cons = check_constraints(h, bounds=bounds, req=req)
    volume = h.length_pp * h.beam * h.draft * h.block_coefficient
    disp = volume * h.density
    cm = h.resolved_cm()
    cp = h.resolved_cp()
    cwp = (1.0 + 2.0 * h.block_coefficient) / 3.0
    lb = h.length_pp / h.beam if h.beam else 0.0
    bt = h.beam / h.draft if h.draft else 0.0
    ld = h.length_pp / h.depth if h.depth else 0.0
    slend = h.length_pp / (volume ** (1.0 / 3.0)) if volume > 0 else 0.0
    gap = abs(volume - req.target_volume_m3) / req.target_volume_m3 if req.target_volume_m3 else 0.0
    freeboard = h.depth - h.draft
    fn = _fn(h)
    wetted = 1.025 * h.length_pp * (h.block_coefficient * h.beam + 1.7 * h.draft)
    lwt = 0.12 * h.length_pp * h.beam * h.depth * (0.85 + 0.15 * h.block_coefficient)
    dwt = disp - lwt
    dwt_gap = abs(dwt - req.target_dwt_t) / req.target_dwt_t if req.target_dwt_t else 0.0
    hold = 0.72 * h.length_pp * h.beam * h.depth * h.block_coefficient
    kb = h.draft * (0.90 - 0.30 * h.block_coefficient)
    i_wp = cwp * h.length_pp * (h.beam**3) / 12.0
    bm = i_wp / volume if volume > 0 else 0.0
    kg = 0.55 * h.depth
    gm = kb + bm - kg
    vs = h.speed_kn
    power = ((disp ** (2.0 / 3.0)) * (vs**3) / h.length_pp) if h.length_pp else 0.0
    res = estimate_resistance(
        length_pp=h.length_pp,
        beam=h.beam,
        draft=h.draft,
        volume_m3=volume,
        wetted_m2=wetted,
        cp=cp,
        cm=cm,
        density=h.density,
        speed_kn=h.speed_kn,
        dwt_t=dwt,
        voyage_nm=req.voyage_nm,
        sea_margin=req.sea_margin,
    )
    vol_pen = 1000.0 * (max(0.0, req.target_volume_m3 - volume) / max(req.target_volume_m3, 1.0)) ** 2
    dwt_pen = 80.0 * (max(0.0, req.target_dwt_t - dwt) / max(req.target_dwt_t, 1.0)) ** 2
    demo = (h.beam / h.length_pp) * (1.0 + h.block_coefficient**2) + vol_pen + dwt_pen + res.pd_kw / 8e4

    extra_v = list(cons.violations)
    extra_w = list(cons.warnings)
    if bounds:
        if dwt < 15_000:
            extra_v.append("教育用 DWT 推定が 15,000 t 未満（OPEN-16。実載貨ではない）")
        if lwt > 0.40 * disp and disp > 0:
            extra_v.append("教育用軽荷重量が排水質量の 40% 超（OPEN-16）")
        if gm < 0.15:
            extra_v.append("GM 指標が 0.15 m 未満（OPEN-20。 Intact GM / IMO ではない）")
        if res.cargo_dwt_t < 12_000:
            extra_v.append("教育用貨物DWTが 12,000 t 未満（燃料・消耗品控除後）")
        if res.pd_kw > 18_000:
            extra_v.append("初期推定 Pd が 18 MW 超（OPEN-24。実船馬力ではない）")
        extra_w.append("Holtrop/ITTC は初期推定。試運転・CFD・船級の推進性能ではない（OPEN-12/24）")
        extra_w.append("復原性・構造・船級規則は未評価（OPEN-06）")
    cons = ConstraintResult(ok=not extra_v, violations=extra_v, warnings=extra_w)

    return Evaluation(
        volume_m3=round(volume, 3),
        displacement_tonnes=round(disp, 3),
        lightweight_t=round(lwt, 3),
        dwt_t=round(dwt, 3),
        dwt_gap=round(dwt_gap, 6),
        hold_volume_m3=round(hold, 3),
        cp=round(cp, 4),
        cm=round(cm, 4),
        cwp=round(cwp, 4),
        l_over_b=round(lb, 4),
        b_over_t=round(bt, 4),
        l_over_d=round(ld, 4),
        slenderness=round(slend, 4),
        freeboard_m=round(freeboard, 3),
        froude=round(fn, 4),
        wetted_surface_m2=round(wetted, 2),
        gm_indicator_m=round(gm, 3),
        power_index=round(power, 2),
        rt_kn=res.rt_kn,
        pe_kw=res.pe_kw,
        pd_kw=res.pd_kw,
        fuel_t_per_day=res.fuel_t_per_day,
        fuel_t=res.fuel_t,
        cargo_dwt_t=res.cargo_dwt_t,
        lcb_pct=res.lcb_pct,
        lwl_m=res.lwl_m,
        form_factor=res.form_factor,
        resistance_curve=res.payload()["curve"],
        demo_score=round(demo, 6),
        volume_gap=round(gap, 6),
        depth=round(h.depth, 3),
        speed_kn=round(h.speed_kn, 3),
        voyage_nm=req.voyage_nm,
        constraints=cons,
        density=h.density,
    )


def _ranges() -> list[tuple[float, float]]:
    return [LPP_RANGE, BEAM_RANGE, DRAFT_RANGE, CB_RANGE, DEPTH_RANGE]


def _hull_from_x(x: list[float] | tuple[float, ...], speed_kn: float = DESIGN_SPEED_KN) -> Hull:
    return Hull(
        length_pp=float(x[0]),
        beam=float(x[1]),
        draft=float(x[2]),
        block_coefficient=float(x[3]),
        depth=float(x[4]) if len(x) > 4 else DEPTH_DEFAULT,
        speed_kn=speed_kn,
    )


def _lhs(rng: random.Random, n: int) -> list[list[float]]:
    ranges = _ranges()
    cols: list[list[float]] = []
    for lo, hi in ranges:
        bins = [lo + (hi - lo) * (i + rng.random()) / n for i in range(n)]
        rng.shuffle(bins)
        cols.append(bins)
    return [[cols[d][i] for d in range(len(ranges))] for i in range(n)]


def _candidate_row(h: Hull, ev: Evaluation, *, source: str, seed: int, index: int) -> dict:
    row = {
        "length_pp": round(h.length_pp, 3),
        "beam": round(h.beam, 3),
        "draft": round(h.draft, 3),
        "block_coefficient": round(h.block_coefficient, 4),
        "prismatic_coefficient": ev.cp,
        "source": source,
        "seed": seed,
        "index": index,
        **ev.payload(),
    }
    row.pop("note", None)
    return row


def pareto_front(
    rows: list[dict],
    *,
    maximize: tuple[str, ...] = ("cargo_dwt_t",),
    minimize: tuple[str, ...] = ("volume_gap", "pd_kw"),
) -> list[dict]:
    """制約通過点の非支配集合。実船最適ではない。"""
    out: list[dict] = []
    for a in rows:
        dominated = False
        for b in rows:
            if b is a:
                continue
            better_or_equal = True
            strictly = False
            for k in maximize:
                if b[k] < a[k]:
                    better_or_equal = False
                    break
                if b[k] > a[k]:
                    strictly = True
            if not better_or_equal:
                continue
            for k in minimize:
                if b[k] > a[k]:
                    better_or_equal = False
                    break
                if b[k] < a[k]:
                    strictly = True
            if better_or_equal and strictly:
                dominated = True
                break
        item = dict(a)
        item["pareto"] = not dominated
        out.append(item)
    return out


def optimize(*, seed: int = 42, samples: int = 36, speed_kn: float | None = None, req: Requirements | None = None) -> list[dict]:
    req = req or Requirements()
    if speed_kn is not None:
        req.speed_kn = speed_kn
    rng = random.Random(seed)
    cands: list[dict] = []
    seen: set[tuple] = set()

    def push(h: Hull, source: str) -> None:
        ev = evaluate(h, bounds=True, req=req)
        if not ev.constraints.ok:
            return
        key = (
            round(h.length_pp, 2),
            round(h.beam, 2),
            round(h.draft, 2),
            round(h.block_coefficient, 3),
            round(h.depth, 2),
        )
        if key in seen:
            return
        seen.add(key)
        cands.append(_candidate_row(h, ev, source=source, seed=seed, index=len(cands)))

    for x in _lhs(rng, max(samples * 3, 24)):
        if len(cands) >= samples:
            break
        push(_hull_from_x(x, req.speed_kn), "lhs")

    tries = 0
    while len(cands) < samples and tries < samples * 40:
        tries += 1
        x = [rng.uniform(lo, hi) for lo, hi in _ranges()]
        push(_hull_from_x(x, req.speed_kn), "random")

    try:
        from scipy.optimize import differential_evolution

        def objective(x):
            h = _hull_from_x(x, req.speed_kn)
            ev = evaluate(h, bounds=True, req=req)
            if not ev.constraints.ok:
                return 1e6
            return ev.volume_gap * 100.0 + ev.dwt_gap * 40.0 + ev.pd_kw / 2.0e4

        res = differential_evolution(
            objective,
            _ranges(),
            seed=seed,
            maxiter=35,
            popsize=7,
            polish=True,
        )
        push(_hull_from_x(res.x, req.speed_kn), "differential_evolution")
    except Exception:
        pass

    return pareto_front(cands)


def _half_breadth(h: Hull, s: float, z: float) -> float:
    """教育用の半幅。線図・オフセットではない。"""
    exp = 0.55 + 2.4 * (1.0 - h.block_coefficient)
    wl = 0.5 * h.beam * max(0.03, 1.0 - abs(s) ** exp)
    if z <= 0:
        return 0.0
    if z <= h.draft:
        eta = z / h.draft if h.draft else 0.0
        p = 1.4 + 4.0 * (1.0 - h.resolved_cm())
        return wl * (eta ** (1.0 / p))
    deck = max(h.depth, h.draft + 0.1)
    eta = min(1.0, (z - h.draft) / (deck - h.draft))
    return wl * (1.0 - 0.05 * eta)


def hull_vertices(h: Hull, n: int = 20) -> list[list[float]]:
    """後方互換の点群。実船線図ではない。"""
    mesh = hull_mesh(h, n_st=n)
    return mesh["points"]


def hull_mesh(h: Hull, n_st: int = 24, n_wl: int = 9) -> dict:
    """ステーションと簡易シェル。設計承認用の線図ではない。"""
    zs = [h.depth * i / (n_wl - 1) for i in range(n_wl)]
    stations: list[list[list[float]]] = []
    points: list[list[float]] = []
    index: list[int] = []
    for i in range(n_st + 1):
        s = 2.0 * i / n_st - 1.0
        x = (i / n_st - 0.5) * h.length_pp
        st: list[list[float]] = []
        for z in zs:
            y = _half_breadth(h, s, z)
            st.append([round(x, 4), round(-y, 4), round(z, 4)])
            st.append([round(x, 4), round(y, 4), round(z, 4)])
        stations.append(st)
        points.extend(st)

    def vid(i: int, j: int, side: int) -> int:
        return i * (n_wl * 2) + j * 2 + side

    for i in range(n_st):
        for j in range(n_wl - 1):
            for side in (0, 1):
                a, b = vid(i, j, side), vid(i, j + 1, side)
                c, d = vid(i + 1, j, side), vid(i + 1, j + 1, side)
                if side == 0:
                    index.extend([a, c, b, b, c, d])
                else:
                    index.extend([a, b, c, b, d, c])

    wl_z = h.draft
    waterline: list[list[float]] = []
    keel: list[list[float]] = []
    deck: list[list[float]] = []
    for i in range(n_st + 1):
        s = 2.0 * i / n_st - 1.0
        x = (i / n_st - 0.5) * h.length_pp
        yw = _half_breadth(h, s, wl_z)
        yd = _half_breadth(h, s, h.depth)
        waterline.append([round(x, 4), round(-yw, 4), round(wl_z, 4)])
        waterline.append([round(x, 4), round(yw, 4), round(wl_z, 4)])
        keel.append([round(x, 4), 0.0, 0.0])
        deck.append([round(x, 4), round(-yd, 4), round(h.depth, 4)])
        deck.append([round(x, 4), round(yd, 4), round(h.depth, 4)])

    return {
        "points": points,
        "index": index,
        "stations": stations,
        "waterline": waterline,
        "keel": keel,
        "deck": deck,
        "note": "educational mesh. not a lines plan.",
    }


def design_report(h: Hull, ev: Evaluation, *, project_name: str = "案件") -> str:
    cons = ev.constraints
    lines = [
        f"# 初期設計レポート（{ev.model_version}）",
        "",
        f"- 案件: {project_name}",
        f"- 船型: Lpp {h.length_pp} m / B {h.beam} m / T {h.draft} m / D {ev.depth} m / Cb {h.block_coefficient}",
        f"- ∇: {ev.volume_m3} m³（Lpp×B×T×Cb）",
        f"- Δ: {ev.displacement_tonnes} t（密度 {ev.density} t/m³）",
        f"- 教育用 DWT: {ev.dwt_t} t / 貨物DWT: {ev.cargo_dwt_t} t / 燃料: {ev.fuel_t} t（航程 {ev.voyage_nm} nm）",
        f"- Fn: {ev.froude} / LCB: {ev.lcb_pct} %L / Lwl: {ev.lwl_m} m",
        f"- 初期推定 Rt: {ev.rt_kn} kN / Pe: {ev.pe_kw} kW / Pd: {ev.pd_kw} kW（海余裕込み）",
        f"- 制約: {'通過' if cons.ok else '違反'}",
        "",
        "## 制約",
    ]
    lines.extend([f"- 違反: {x}" for x in cons.violations] or ["- 違反なし"])
    lines.extend([f"- 警告: {x}" for x in cons.warnings])
    lines.extend(
        [
            "",
            "## 未評価",
            "- 復原性（IMO）、構造、船級規則、試運転抵抗、CFD、プロペラ設計",
            "",
            "## 注意",
            ev.note,
            "AI推奨を正式設計に採用するには設計者と船級の確認が必要です。",
        ]
    )
    return "\n".join(lines)
