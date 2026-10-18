"""Holtrop 1982 系の初期推定。試運転・CFD・船級の抵抗ではない（OPEN-24）。"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

G = 9.81
NU_SEA = 1.188e-6  # m²/s at 15 °C
CA = 0.0004
ETA_D = 0.62  # OPEN-27 総合推進効率の仮定
SFOC_G_KWH = 180.0  # OPEN-25 燃料消費率の仮定
SEA_MARGIN = 0.15
LWL_FACTOR = 1.01  # OPEN-26 Lwl ≈ 1.01 Lpp


@dataclass
class SpeedPoint:
    speed_kn: float
    froude: float
    rt_kn: float
    pe_kw: float
    pd_kw: float
    fuel_t_per_day: float


@dataclass
class Resistance:
    method: str
    rn: float
    cf: float
    form_factor: float
    lcb_pct: float
    lwl_m: float
    rv_kn: float
    rw_kn: float
    rt_kn: float
    pe_kw: float
    pd_kw: float
    sea_margin: float
    eta_d: float
    sfoc_g_kwh: float
    fuel_t_per_day: float
    fuel_t: float
    range_nm: float
    stores_t: float
    fresh_water_t: float
    cargo_dwt_t: float
    curve: list[SpeedPoint] = field(default_factory=list)
    note: str = (
        "Holtrop-1982 subset + ITTC-57. preliminary empirical estimate. "
        "not speed trial. not CFD. not class-approved propulsion."
    )

    def payload(self) -> dict:
        data = asdict(self)
        data["curve"] = [asdict(p) for p in self.curve]
        return data


def lwl_m(length_pp: float) -> float:
    return LWL_FACTOR * length_pp


def lcb_percent(cp: float) -> float:
    """amidships からの LCB [%L]。正が船首。ばら積みの教育用（OPEN-29）。"""
    return round(9.0 * (cp - 0.68) - 2.0, 3)


def ittc57_cf(rn: float) -> float:
    rn = max(rn, 1.0e5)
    return 0.075 / (math.log10(rn) - 2.0) ** 2


def _form_factor(length: float, beam: float, draft: float, volume: float, cp: float) -> float:
    if min(length, beam, draft, volume) <= 0 or cp >= 1:
        return 1.2
    lr = length * (1.0 - cp + 0.06 * cp * lcb_percent(cp) / max(4.0 * cp - 1.0, 0.15))
    lr = max(lr, 0.15 * length)
    k = (
        0.93
        + 0.487118
        * (beam / length) ** 1.06806
        * (draft / length) ** 0.46106
        * (length / lr) ** 0.121563
        * ((length**3) / volume) ** 0.36486
        * (1.0 - cp) ** (-0.604247)
    )
    return max(1.05, min(float(k), 1.8))


def _wave_n(length: float, beam: float, draft: float, volume: float, cp: float, cm: float, v_ms: float, rho: float) -> float:
    if v_ms <= 0.3 or volume <= 0:
        return 0.0
    fn = v_ms / math.sqrt(G * length)
    fn = min(max(fn, 0.08), 0.40)
    if cp < 0.8:
        c16 = 8.07981 * cp - 13.8673 * cp**2 + 6.984388 * cp**3
    else:
        c16 = 1.73014 - 0.7067 * cp
    m1 = 0.0140407 * length / draft - 1.75254 * (volume ** (1.0 / 3.0)) / length - 4.79323 * beam / length - c16
    slend = length / (volume ** (1.0 / 3.0))
    if slend**3 < 512:
        c15 = -1.69385
    elif slend**3 > 1727:
        c15 = 0.0
    else:
        c15 = -1.69385 + (slend - 8.0) / 2.36
    m2 = c15 * cp**2 * math.exp(-0.1 * fn ** (-2.0))
    lam = 1.446 * cp - 0.03 * length / beam
    c17 = 6919.3 * (cm ** (-1.3346)) * (volume / length**3) ** 2.00977 * max(length / beam - 2.0, 0.08) ** 1.40692
    rw = c17 * volume * rho * G * math.exp(m1 * fn ** (-0.9) + m2 * math.cos(lam * fn ** (-2.0)))
    return max(0.0, float(rw))


def estimate_at_speed(
    *,
    length_pp: float,
    beam: float,
    draft: float,
    volume_m3: float,
    wetted_m2: float,
    cp: float,
    cm: float,
    density: float,
    speed_kn: float,
) -> tuple[float, float, float, float, float, float, float]:
    """Returns Fn, Rn, Cf, 1+k, Rv[N], Rw[N], Rt[N]."""
    length = lwl_m(length_pp)
    v = speed_kn * 1852.0 / 3600.0
    rho = density * 1000.0
    fn = v / math.sqrt(G * length) if length else 0.0
    rn = v * length / NU_SEA if v > 0 else 0.0
    cf = ittc57_cf(rn)
    k1 = _form_factor(length, beam, draft, volume_m3, cp)
    rv = 0.5 * rho * wetted_m2 * v * v * (cf * k1 + CA)
    rw = _wave_n(length, beam, draft, volume_m3, cp, cm, v, rho)
    rt = (rv + rw) * 1.03  # OPEN-24 付加物 3%
    return fn, rn, cf, k1, rv, rw, rt


def fuel_plan(pd_kw: float, speed_kn: float, dwt_t: float, voyage_nm: float) -> tuple[float, float, float, float, float, float]:
    tpd = pd_kw * 24.0 * SFOC_G_KWH / 1_000_000.0
    days = voyage_nm / max(speed_kn * 24.0, 0.1)
    fuel = tpd * days * 1.10
    stores = 0.02 * max(dwt_t, 0.0)
    water = 0.01 * max(dwt_t, 0.0)
    cargo = dwt_t - fuel - stores - water
    return tpd, fuel, stores, water, cargo, voyage_nm


def estimate(
    *,
    length_pp: float,
    beam: float,
    draft: float,
    volume_m3: float,
    wetted_m2: float,
    cp: float,
    cm: float,
    density: float,
    speed_kn: float,
    dwt_t: float,
    voyage_nm: float = 6000.0,
    sea_margin: float = SEA_MARGIN,
) -> Resistance:
    fn, rn, cf, k1, rv, rw, rt = estimate_at_speed(
        length_pp=length_pp,
        beam=beam,
        draft=draft,
        volume_m3=volume_m3,
        wetted_m2=wetted_m2,
        cp=cp,
        cm=cm,
        density=density,
        speed_kn=speed_kn,
    )
    v = speed_kn * 1852.0 / 3600.0
    pe = rt * v / 1000.0
    pd = pe * (1.0 + sea_margin) / ETA_D if ETA_D else pe
    tpd, fuel, stores, water, cargo, rng = fuel_plan(pd, speed_kn, dwt_t, voyage_nm)
    curve: list[SpeedPoint] = []
    for kn in (10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0):
        fn_i, _, _, _, _, _, rt_i = estimate_at_speed(
            length_pp=length_pp,
            beam=beam,
            draft=draft,
            volume_m3=volume_m3,
            wetted_m2=wetted_m2,
            cp=cp,
            cm=cm,
            density=density,
            speed_kn=kn,
        )
        v_i = kn * 1852.0 / 3600.0
        pe_i = rt_i * v_i / 1000.0
        pd_i = pe_i * (1.0 + sea_margin) / ETA_D
        tpd_i = pd_i * 24.0 * SFOC_G_KWH / 1_000_000.0
        curve.append(
            SpeedPoint(
                speed_kn=kn,
                froude=round(fn_i, 4),
                rt_kn=round(rt_i / 1000.0, 2),
                pe_kw=round(pe_i, 1),
                pd_kw=round(pd_i, 1),
                fuel_t_per_day=round(tpd_i, 3),
            )
        )
    return Resistance(
        method="holtrop-1982-subset+ITTC57",
        rn=round(rn, 3),
        cf=round(cf, 6),
        form_factor=round(k1, 4),
        lcb_pct=lcb_percent(cp),
        lwl_m=round(lwl_m(length_pp), 3),
        rv_kn=round(rv / 1000.0, 2),
        rw_kn=round(rw / 1000.0, 2),
        rt_kn=round(rt / 1000.0, 2),
        pe_kw=round(pe, 1),
        pd_kw=round(pd, 1),
        sea_margin=sea_margin,
        eta_d=ETA_D,
        sfoc_g_kwh=SFOC_G_KWH,
        fuel_t_per_day=round(tpd, 3),
        fuel_t=round(fuel, 3),
        range_nm=round(rng, 1),
        stores_t=round(stores, 3),
        fresh_water_t=round(water, 3),
        cargo_dwt_t=round(cargo, 3),
        curve=curve,
    )
