import math

from app.engine import (
    DESIGN_SPEED_KN,
    G_M_S2,
    KN_TO_MS,
    Hull,
    Requirements,
    check_constraints,
    design_report,
    evaluate,
    hull_mesh,
    optimize,
)


def test_volume_formula():
    ev = evaluate(Hull(180, 30, 10, 0.75))
    assert ev.volume_m3 == 40500.0
    assert ev.displacement_tonnes == round(40500 * 1.025, 3)
    assert ev.constraints.ok


def test_reject_bad_cb():
    r = check_constraints(Hull(180, 30, 10, 0))
    assert not r.ok


def test_cb_gt_cp():
    r = check_constraints(Hull(180, 30, 10, 0.9, 0.8))
    assert not r.ok


def test_cb_gt_cm():
    r = check_constraints(Hull(180, 30, 10, 0.9, midship_coefficient=0.85))
    assert not r.ok


def test_practical_mass_and_froude():
    ev = evaluate(Hull(180, 30, 10, 0.75, depth=16.0, speed_kn=14.0))
    fn = (DESIGN_SPEED_KN * KN_TO_MS) / math.sqrt(G_M_S2 * 180)
    assert ev.froude == round(fn, 4)
    assert ev.lightweight_t > 8_000
    assert ev.dwt_t == round(ev.displacement_tonnes - ev.lightweight_t, 3)
    assert ev.dwt_t > 20_000
    assert ev.hold_volume_m3 > 40_000
    assert ev.wetted_surface_m2 > 5_000
    assert ev.power_index > 0
    assert ev.gm_indicator_m > 0.15
    assert ev.freeboard_m == 6.0
    assert ev.cp == round(0.75 / 0.98, 4)
    assert 50 < ev.rt_kn < 8000
    assert 500 < ev.pd_kw < 18000
    assert ev.cargo_dwt_t < ev.dwt_t
    assert len(ev.resistance_curve) >= 5
    assert ev.resistance_curve[-1]["pd_kw"] > ev.resistance_curve[0]["pd_kw"]


def test_freeboard_bounds():
    r = check_constraints(Hull(180, 30, 10, 0.75, depth=11.0), bounds=True)
    assert not r.ok
    assert any("乾舷" in x for x in r.violations)


def test_canal_warning_not_hard_fail():
    ev = evaluate(Hull(180, 33.0, 10, 0.75, depth=16.0), bounds=True)
    assert any("パナマ" in x for x in ev.constraints.warnings)


def test_optimize_reproducible():
    a = optimize(seed=42, samples=12)
    b = optimize(seed=42, samples=12)
    assert a and a[0]["length_pp"] == b[0]["length_pp"]
    assert all(c["constraints"]["ok"] for c in a)
    assert any(c.get("pareto") for c in a)
    assert all("dwt_t" in c and "pd_kw" in c and "cargo_dwt_t" in c for c in a)


def test_panama_enforced():
    req = Requirements(enforce_panama=True)
    ev = evaluate(Hull(180, 33.0, 10, 0.75, depth=16.0), bounds=True, req=req)
    assert not ev.constraints.ok
    assert any("パナマ" in x for x in ev.constraints.violations)


def test_report_mentions_volume_formula():
    h = Hull(180, 30, 10, 0.75, depth=16.0)
    md = design_report(h, evaluate(h))
    assert "Lpp×B×T×Cb" in md
    assert "geom-v3" in md


def test_hull_mesh_has_waterline():
    mesh = hull_mesh(Hull(180, 30, 10, 0.75, depth=16.0))
    assert len(mesh["points"]) > 50
    assert len(mesh["index"]) > 50
    assert mesh["waterline"]
    assert all(abs(p[2] - 10.0) < 1e-6 for p in mesh["waterline"])
