from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.env import openai_configured, openai_model
from app.llm import LlmConfigError, explain_evaluation, extract_spec
from app.db import Base, SessionLocal, engine, get_db
from app.engine import (
    MODEL_VERSION,
    TARGET_DWT_T,
    TARGET_VOLUME_M3,
    Hull,
    Requirements,
    design_report,
    evaluate,
    hull_mesh,
    hull_vertices,
    optimize,
)
from app.models import AuditLog, Candidate, OptimizationJob, Project, Review
from app.schemas import ExplainIn, ExtractIn, HullIn, OptimizeIn, ProjectIn, ProjectPatch, ReviewIn

OPEN = {
    "OPEN-01": "Handymax bulk",
    "OPEN-03": "design speed 14 kn (Froude indicator only)",
    "OPEN-07": "density 1.025 t/m3",
    "OPEN-08": "volume = Lpp*B*T*Cb",
    "OPEN-13": "Cm default 0.98; Cp = Cb/Cm",
    "OPEN-16": "LWT/DWT are educational mass split, not lightweight survey",
    "OPEN-23": "LLM is spec extraction and explanation only. Not a physics model.",
    "OPEN-24": "Holtrop-1982 subset + ITTC-57. not trial/CFD/class",
    "disclaimer": "教育用。船級承認・航行安全・実船抵抗の判定には使えない。",
}

METRIC_KEYS = (
    "l_over_b",
    "b_over_t",
    "l_over_d",
    "slenderness",
    "source",
    "cp",
    "cm",
    "cwp",
    "depth",
    "speed_kn",
    "froude",
    "wetted_surface_m2",
    "lightweight_t",
    "dwt_t",
    "dwt_gap",
    "hold_volume_m3",
    "gm_indicator_m",
    "power_index",
    "rt_kn",
    "pe_kw",
    "pd_kw",
    "fuel_t_per_day",
    "fuel_t",
    "cargo_dwt_t",
    "lcb_pct",
    "lwl_m",
    "form_factor",
    "resistance_curve",
    "voyage_nm",
    "freeboard_m",
    "warnings",
)


def default_assumptions(req: Requirements | None = None) -> dict:
    return {**OPEN, "req": (req or Requirements()).as_dict()}


def req_from_project(p: Project | None) -> Requirements:
    if not p or not p.assumptions:
        return Requirements()
    return Requirements.from_dict(p.assumptions.get("req") if isinstance(p.assumptions, dict) else None)


def project_out(p: Project) -> dict:
    return {
        "id": str(p.id),
        "name": p.name,
        "vessel_type": p.vessel_type,
        "assumptions": p.assumptions,
        "requirements": req_from_project(p).as_dict(),
        "unassessed": ["stability", "scantlings", "class_rules", "propulsion_trial", "seakeeping"],
    }


def jsonable(obj):
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    return obj


def audit(db: Session, action: str, payload: dict):
    db.add(AuditLog(action=action, payload=jsonable(payload)))


def seed(db: Session):
    if db.query(Project).count():
        return
    p = Project(
        name="デモ案件（OPEN仮定）",
        vessel_type="Handymax bulk (OPEN-01)",
        assumptions=default_assumptions(),
    )
    db.add(p)
    audit(db, "project.seed", {"name": p.name})
    db.commit()


def hull_from_body(body: HullIn) -> Hull:
    return Hull(
        length_pp=body.length_pp,
        beam=body.beam,
        draft=body.draft,
        block_coefficient=body.block_coefficient,
        prismatic_coefficient=body.prismatic_coefficient,
        density=body.density,
        depth=body.depth,
        speed_kn=body.speed_kn,
        midship_coefficient=body.midship_coefficient,
    )


def hull_from_candidate(c: Candidate) -> Hull:
    m = c.metrics or {}
    return Hull(
        c.length_pp,
        c.beam,
        c.draft,
        c.block_coefficient,
        c.prismatic_coefficient,
        depth=float(m.get("depth", 16.0)),
        speed_kn=float(m.get("speed_kn", 14.0)),
        midship_coefficient=float(m["cm"]) if "cm" in m else None,
    )


def candidate_out(c: Candidate) -> dict:
    h = hull_from_candidate(c)
    m = c.metrics or {}
    return {
        "id": str(c.id),
        "length_pp": c.length_pp,
        "beam": c.beam,
        "draft": c.draft,
        "block_coefficient": c.block_coefficient,
        "prismatic_coefficient": c.prismatic_coefficient,
        "volume_m3": c.volume_m3,
        "displacement_tonnes": c.displacement_tonnes,
        "demo_score": c.demo_score,
        "volume_gap": c.volume_gap,
        "pareto": c.pareto,
        "adopted": c.adopted,
        "metrics": m,
        "depth": m.get("depth"),
        "dwt_t": m.get("dwt_t"),
        "lightweight_t": m.get("lightweight_t"),
        "froude": m.get("froude"),
        "power_index": m.get("power_index"),
        "pd_kw": m.get("pd_kw"),
        "rt_kn": m.get("rt_kn"),
        "cargo_dwt_t": m.get("cargo_dwt_t"),
        "fuel_t": m.get("fuel_t"),
        "resistance_curve": m.get("resistance_curve"),
        "gm_indicator_m": m.get("gm_indicator_m"),
        "hold_volume_m3": m.get("hold_volume_m3"),
        "model_version": c.model_version,
        "seed": c.seed,
        "mesh": hull_vertices(h),
        "surface": hull_mesh(h),
    }


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("SKIP_DB_INIT") != "1":
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="Ship Design AI",
    version=MODEL_VERSION,
    description="Educational preliminary ship design. Not for class approval or measured resistance.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGIN", "http://localhost:3060").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": MODEL_VERSION,
        "open": OPEN,
        "targets": {"volume_m3": TARGET_VOLUME_M3, "dwt_t": TARGET_DWT_T},
        "openai": {
            "configured": openai_configured(),
            "model": openai_model() if openai_configured() else None,
            "role": "spec extraction and explanation only",
        },
    }


@app.post("/api/projects")
def create_project(body: ProjectIn, db: Session = Depends(get_db)):
    req = Requirements.from_dict(body.requirements.model_dump() if body.requirements else None)
    p = Project(name=body.name, vessel_type=body.vessel_type, assumptions=default_assumptions(req))
    db.add(p)
    audit(db, "project.create", {"name": body.name})
    db.commit()
    db.refresh(p)
    return project_out(p)


@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    rows = db.query(Project).order_by(Project.created_at.desc()).all()
    return [project_out(p) for p in rows]


@app.get("/api/projects/{pid}")
def get_project(pid: uuid.UUID, db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "project not found")
    return project_out(p)


@app.patch("/api/projects/{pid}")
def patch_project(pid: uuid.UUID, body: ProjectPatch, db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "project not found")
    if body.name:
        p.name = body.name
    if body.requirements:
        current = dict(p.assumptions or {})
        current.update(OPEN)
        current["req"] = Requirements.from_dict(body.requirements.model_dump()).as_dict()
        p.assumptions = current
    audit(db, "project.patch", {"id": str(p.id)})
    db.commit()
    db.refresh(p)
    return project_out(p)


@app.post("/api/design/evaluate")
def evaluate_design(body: HullIn, db: Session = Depends(get_db)):
    req = Requirements()
    if body.requirements:
        req = Requirements.from_dict(body.requirements.model_dump())
    elif body.project_id:
        p = db.get(Project, body.project_id)
        if not p:
            raise HTTPException(404, "project not found")
        req = req_from_project(p)
    h = hull_from_body(body)
    ev = evaluate(h, bounds=body.check_bounds, req=req)
    audit(
        db,
        "design.evaluate",
        {
            "input": body.model_dump(mode="json"),
            "volume_m3": ev.volume_m3,
            "dwt_t": ev.dwt_t,
            "ok": ev.constraints.ok,
            "model": MODEL_VERSION,
        },
    )
    db.commit()
    return {
        **ev.payload(),
        "mesh": hull_vertices(h) if ev.constraints.ok else [],
        "surface": hull_mesh(h) if ev.constraints.ok else None,
        "open": OPEN,
        "unassessed": ["stability", "scantlings", "class_rules", "propulsion", "seakeeping"],
    }


@app.post("/api/design/extract")
def extract_design(body: ExtractIn, db: Session = Depends(get_db)):
    try:
        extracted = extract_spec(body.text)
    except LlmConfigError as e:
        raise HTTPException(503, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(502, "OpenAI の仕様抽出に失敗しました") from e

    hull_kwargs = {
        "length_pp": extracted.get("length_pp", 180.0),
        "beam": extracted.get("beam", 30.0),
        "draft": extracted.get("draft", 10.0),
        "block_coefficient": extracted.get("block_coefficient", 0.75),
        "depth": extracted.get("depth", 16.0),
        "speed_kn": extracted.get("speed_kn", 14.0),
    }
    h = Hull(**hull_kwargs)
    ev = evaluate(h, bounds=True)
    audit(
        db,
        "design.extract",
        {"fields": [k for k in extracted if k in ("length_pp", "beam", "draft", "depth", "block_coefficient", "speed_kn")], "ok": ev.constraints.ok},
    )
    db.commit()
    return {
        "hull": hull_kwargs,
        "extracted": {k: extracted[k] for k in extracted if k not in {"model", "role"}},
        "missing": [k for k in ("length_pp", "beam", "draft", "depth", "block_coefficient", "speed_kn") if k not in extracted],
        "evaluation": ev.payload(),
        "model": extracted.get("model"),
        "note": "数値の確定は geom-v3。LLM は抽出のみ。船級承認ではない。",
        "open": OPEN,
    }


@app.post("/api/design/explain")
def explain_design(body: ExplainIn, db: Session = Depends(get_db)):
    h = Hull(
        length_pp=body.length_pp,
        beam=body.beam,
        draft=body.draft,
        block_coefficient=body.block_coefficient,
        depth=body.depth,
        speed_kn=body.speed_kn,
    )
    ev = evaluate(h, bounds=body.check_bounds)
    try:
        explained = explain_evaluation(ev.payload())
    except LlmConfigError as e:
        raise HTTPException(503, str(e)) from e
    except Exception as e:
        raise HTTPException(502, "OpenAI の説明生成に失敗しました") from e
    audit(db, "design.explain", {"volume_m3": ev.volume_m3, "ok": ev.constraints.ok, "model": explained["model"]})
    db.commit()
    return {**explained, "evaluation": ev.payload(), "open": OPEN}


def _run_job(job_id: uuid.UUID, samples: int, req_data: dict):
    db = SessionLocal()
    try:
        job = db.get(OptimizationJob, job_id)
        if not job:
            return
        job.status = "running"
        db.commit()
        req = Requirements.from_dict(req_data)
        rows = optimize(seed=job.seed, samples=samples, req=req)
        for r in rows:
            db.add(
                Candidate(
                    project_id=job.project_id,
                    job_id=job.id,
                    length_pp=r["length_pp"],
                    beam=r["beam"],
                    draft=r["draft"],
                    block_coefficient=r["block_coefficient"],
                    prismatic_coefficient=r["prismatic_coefficient"],
                    volume_m3=r["volume_m3"],
                    displacement_tonnes=r["displacement_tonnes"],
                    demo_score=r["demo_score"],
                    volume_gap=r["volume_gap"],
                    pareto=bool(r.get("pareto")),
                    feasible=True,
                    metrics={k: r[k] for k in METRIC_KEYS if k in r}
                    | {"warnings": (r.get("constraints") or {}).get("warnings", [])},
                    model_version=MODEL_VERSION,
                    seed=job.seed,
                )
            )
        job.status = "done"
        job.result_count = len(rows)
        job.finished_at = datetime.now(timezone.utc)
        audit(db, "optimization.done", {"job_id": str(job.id), "count": len(rows), "seed": job.seed})
        db.commit()
    except Exception as e:
        db.rollback()
        job = db.get(OptimizationJob, job_id)
        if job:
            job.status = "failed"
            job.error = str(e)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@app.post("/api/optimization/jobs", status_code=202)
def start_job(body: OptimizeIn, bg: BackgroundTasks, db: Session = Depends(get_db)):
    p = db.get(Project, body.project_id)
    if not p:
        raise HTTPException(404, "project not found")
    req = req_from_project(p)
    if body.speed_kn is not None:
        req.speed_kn = body.speed_kn
    job = OptimizationJob(project_id=p.id, seed=body.seed, model_version=MODEL_VERSION, status="queued")
    db.add(job)
    audit(db, "optimization.queued", {"project_id": str(p.id), "seed": body.seed, "speed_kn": req.speed_kn})
    db.commit()
    db.refresh(job)
    bg.add_task(_run_job, job.id, body.samples, req.as_dict())
    return {"job_id": str(job.id), "status": job.status, "model_version": MODEL_VERSION}


@app.get("/api/optimization/jobs/{jid}")
def get_job(jid: uuid.UUID, db: Session = Depends(get_db)):
    job = db.get(OptimizationJob, jid)
    if not job:
        raise HTTPException(404, "job not found")
    return {
        "job_id": str(job.id),
        "status": job.status,
        "seed": job.seed,
        "model_version": job.model_version,
        "result_count": job.result_count,
        "error": job.error,
    }


@app.get("/api/projects/{pid}/candidates")
def list_candidates(pid: uuid.UUID, pareto: bool = False, model: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Candidate).filter(Candidate.project_id == pid)
    if pareto:
        q = q.filter(Candidate.pareto.is_(True))
    if model:
        q = q.filter(Candidate.model_version == model)
    rows = q.order_by(Candidate.demo_score.asc()).all()
    return [candidate_out(c) for c in rows]


@app.get("/api/projects/{pid}/compare")
def compare_candidates(pid: uuid.UUID, a: uuid.UUID, b: uuid.UUID, db: Session = Depends(get_db)):
    ca = db.get(Candidate, a)
    cb = db.get(Candidate, b)
    if not ca or not cb or ca.project_id != pid or cb.project_id != pid:
        raise HTTPException(404, "candidate not found")
    keys = ("length_pp", "beam", "draft", "block_coefficient", "volume_m3", "dwt_t", "cargo_dwt_t", "pd_kw", "rt_kn", "froude")
    left, right = candidate_out(ca), candidate_out(cb)
    delta = {}
    for k in keys:
        va, vb = left.get(k), right.get(k)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            delta[k] = round(vb - va, 4)
    return {"a": left, "b": right, "delta_b_minus_a": delta, "note": "差は教育用指標。実船性能差ではない。"}


@app.post("/api/design/report")
def report_design(body: HullIn, db: Session = Depends(get_db)):
    req = Requirements()
    name = "案件"
    if body.requirements:
        req = Requirements.from_dict(body.requirements.model_dump())
    if body.project_id:
        p = db.get(Project, body.project_id)
        if not p:
            raise HTTPException(404, "project not found")
        if not body.requirements:
            req = req_from_project(p)
        name = p.name
    h = hull_from_body(body)
    ev = evaluate(h, bounds=body.check_bounds, req=req)
    md = design_report(h, ev, project_name=name)
    audit(db, "design.report", {"volume_m3": ev.volume_m3, "pd_kw": ev.pd_kw})
    db.commit()
    return {"markdown": md, "evaluation": ev.payload(), "model_version": MODEL_VERSION, "open": OPEN}


@app.post("/api/design/reviews")
def add_review(body: ReviewIn, db: Session = Depends(get_db)):
    c = db.get(Candidate, body.candidate_id)
    if not c or c.project_id != body.project_id:
        raise HTTPException(404, "candidate not found")
    r = Review(
        project_id=body.project_id,
        candidate_id=body.candidate_id,
        decision=body.decision,
        comment=body.comment,
        reviewer=body.reviewer,
    )
    db.add(r)
    if body.decision == "approved":
        c.adopted = True
    if body.decision == "rejected":
        c.adopted = False
    audit(
        db,
        "design.review",
        {"candidate_id": str(c.id), "decision": body.decision, "reviewer": body.reviewer},
    )
    db.commit()
    return {
        "id": str(r.id),
        "decision": r.decision,
        "note": "AI推奨は設計者の承認後も船級確認が必要（Skill品質ゲート）",
    }
