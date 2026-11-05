"""
schemas.py — Pydantic request/response models
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────────────

class MatchRequest(BaseModel):
    """Find matching grants for an existing startup (by ID) or an ad-hoc profile."""
    startup_id: Optional[str] = Field(None, description="ID from startup_profiles_80.csv (e.g. ST014)")
    sector: Optional[str] = Field(None, description="Sector override / ad-hoc query")
    stage: Optional[str] = Field(None, description="Stage override / ad-hoc query")
    dpiit_recognized: Optional[str] = Field(None, description="'Yes' or 'No'")
    min_score: float = Field(0.3, ge=0.0, le=1.0, description="Minimum match score filter")
    max_results: int = Field(10, ge=1, le=15, description="Max grants to return")


class ProposalRequest(BaseModel):
    startup_id: str = Field(..., description="Startup ID from dataset")
    grant_id: str = Field(..., description="Grant ID from dataset")


class EligibilityRequest(BaseModel):
    startup_id: str
    grant_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    stage: float
    sector: float
    dpiit: float
    deadline: float
    funding: float


class GrantMatch(BaseModel):
    grant_id: str
    grant_name: str
    offering_body: str
    max_funding_amount_inr: int
    eligible_stages: List[str]
    eligible_sectors: List[str]
    key_requirements: str
    application_deadline: str
    match_score: float
    score_breakdown: ScoreBreakdown


class MatchResponse(BaseModel):
    startup_id: Optional[str]
    sector: str
    stage: str
    dpiit_recognized: str
    matches: List[GrantMatch]
    total_matches: int


class ProposalResponse(BaseModel):
    startup_id: str
    grant_id: str
    grant_name: str
    company_name: str
    proposal_text: str
    model_used: str


class EligibilityResponse(BaseModel):
    startup_id: str
    grant_id: str
    analysis: str
    model_used: str


class GrantSummaryResponse(BaseModel):
    grant_id: str
    grant_name: str
    summary: str
    model_used: str


class StartupProfile(BaseModel):
    startup_id: str
    company_name: str
    sector: str
    stage: str
    city: str
    state: str
    dpiit_recognized: str
    tech_focus: str
    annual_revenue_inr: float


class GrantScheme(BaseModel):
    grant_id: str
    grant_name: str
    offering_body: str
    max_funding_amount_inr: int
    eligible_stages: List[str]
    eligible_sectors: List[str]
    min_dpiit_recognized: str
    key_requirements: str
    application_deadline: str


class StatisticsResponse(BaseModel):
    total_grants: int
    total_startups: int
    total_max_funding_inr: int
    offering_bodies: List[str]
    sectors_covered: List[str]
    stages_in_dataset: List[str]
    top_sectors: Dict[str, int]
