from uuid import UUID
from pydantic import BaseModel, Field

from app.engine import DESIGN_SPEED_KN, DEPTH_DEFAULT, SEAWATER_DENSITY_T_PER_M3


class RequirementsIn(BaseModel):
    target_volume_m3: float = Field(default=40000, gt=0)
    target_dwt_t: float = Field(default=32000, gt=0)
    speed_kn: float = Field(default=DESIGN_SPEED_KN, gt=0, le=30)
    voyage_nm: float = Field(default=6000, gt=0, le=20000)
    max_beam_m: float | None = Field(default=None, gt=0)
    max_draft_m: float | None = Field(default=None, gt=0)
    enforce_panama: bool = False
    sea_margin: float = Field(default=0.15, ge=0, le=0.4)


class HullIn(BaseModel):
    project_id: UUID | None = None
    requirements: RequirementsIn | None = None
    length_pp: float = Field(gt=0)
    beam: float = Field(gt=0)
    draft: float = Field(gt=0)
    block_coefficient: float = Field(gt=0, le=1)
    prismatic_coefficient: float | None = Field(default=None, gt=0, le=1)
    density: float = Field(default=SEAWATER_DENSITY_T_PER_M3, gt=0)
    depth: float = Field(default=DEPTH_DEFAULT, gt=0)
    speed_kn: float = Field(default=DESIGN_SPEED_KN, gt=0, le=30)
    midship_coefficient: float | None = Field(default=None, gt=0, le=1)
    check_bounds: bool = False


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    vessel_type: str = "Handymax bulk (OPEN-01)"
    requirements: RequirementsIn | None = None


class ProjectPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    requirements: RequirementsIn | None = None


class OptimizeIn(BaseModel):
    project_id: UUID
    seed: int = 42
    samples: int = Field(default=48, ge=8, le=80)
    speed_kn: float | None = Field(default=None, gt=0, le=30)


class ReviewIn(BaseModel):
    project_id: UUID
    candidate_id: UUID
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str = ""
    reviewer: str = "designer"


class ExtractIn(BaseModel):
    text: str = Field(min_length=4, max_length=4000)


class ExplainIn(BaseModel):
    length_pp: float = Field(gt=0)
    beam: float = Field(gt=0)
    draft: float = Field(gt=0)
    block_coefficient: float = Field(gt=0, le=1)
    depth: float = Field(default=DEPTH_DEFAULT, gt=0)
    speed_kn: float = Field(default=DESIGN_SPEED_KN, gt=0, le=30)
    check_bounds: bool = True
