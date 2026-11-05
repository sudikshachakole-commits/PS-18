"""
main.py — FastAPI application entry point

Routes:
  GET  /                        → Serve UI (index.html)
  GET  /api/startups            → List all startup profiles
  GET  /api/startups/{id}       → Get single startup profile
  GET  /api/grants              → List all grant schemes
  GET  /api/grants/{id}         → Get single grant + plain-language summary
  POST /api/match               → Match grants to a startup
  POST /api/proposal            → Generate grant application draft (IBM Granite)
  POST /api/eligibility         → Analyse startup–grant eligibility (IBM Granite)
  GET  /api/statistics          → Dashboard statistics
  GET  /health                  → Health check
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

import data_loader
from config import settings
from granite_client import (
    generate_eligibility_analysis,
    generate_grant_summary,
    generate_proposal,
)
from matcher import get_statistics, match_grants_for_startup
from schemas import (
    EligibilityRequest,
    EligibilityResponse,
    GrantMatch,
    GrantScheme,
    GrantSummaryResponse,
    MatchRequest,
    MatchResponse,
    ProposalRequest,
    ProposalResponse,
    ScoreBreakdown,
    StartupProfile,
    StatisticsResponse,
)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Grant & Funding Finder for Startups",
    description=(
        "Matches Indian startups with relevant government grants and generates "
        "tailored application proposals using IBM Granite / watsonx.ai."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static assets (CSS, JS, images if any)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
async def _startup():
    data_loader.load_all()
    logger.info("Application ready on %s:%s", settings.APP_HOST, settings.APP_PORT)


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=FileResponse, include_in_schema=False)
async def serve_ui():
    ui_path = Path(__file__).parent / "static" / "index.html"
    if not ui_path.exists():
        raise HTTPException(status_code=404, detail="UI not found")
    return FileResponse(str(ui_path))


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    df = data_loader.get_startups_df()
    grants = data_loader.get_grants()
    return {
        "status": "ok",
        "startups_loaded": len(df),
        "grants_loaded": len(grants),
        "granite_backend": settings.PROPOSAL_BACKEND,
        "granite_model": settings.GRANITE_MODEL_ID,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Startups
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/startups", response_model=List[StartupProfile], tags=["Startups"])
async def list_startups(sector: str = None, stage: str = None, dpiit: str = None):
    """List all startup profiles, optionally filtered."""
    df = data_loader.get_startups_df()
    if sector:
        df = df[df["sector"].str.lower() == sector.lower()]
    if stage:
        df = df[df["stage"].str.lower() == stage.lower()]
    if dpiit:
        df = df[df["dpiit_recognized"].str.lower() == dpiit.lower()]
    return df.to_dict(orient="records")


@app.get("/api/startups/{startup_id}", response_model=StartupProfile, tags=["Startups"])
async def get_startup(startup_id: str):
    profile = data_loader.get_startup_by_id(startup_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Startup '{startup_id}' not found")
    return profile


# ─────────────────────────────────────────────────────────────────────────────
# Grants
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/grants", response_model=List[GrantScheme], tags=["Grants"])
async def list_grants():
    return data_loader.get_grants()


@app.get("/api/grants/{grant_id}", tags=["Grants"])
async def get_grant(grant_id: str, summarize: bool = False):
    grant = data_loader.get_grant_by_id(grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail=f"Grant '{grant_id}' not found")
    result = dict(grant)
    if summarize:
        result["plain_summary"] = generate_grant_summary(grant)
        result["model_used"] = settings.GRANITE_MODEL_ID
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Matching
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/match", response_model=MatchResponse, tags=["Matching"])
async def match_grants(req: MatchRequest):
    """
    Core matching endpoint. Supply a startup_id (from dataset) or raw
    sector/stage/dpiit_recognized fields for an ad-hoc query.
    """
    if not req.startup_id and not all([req.sector, req.stage, req.dpiit_recognized]):
        raise HTTPException(
            status_code=422,
            detail="Provide either startup_id OR all of sector, stage, dpiit_recognized.",
        )

    # Resolve profile info for response labels
    sector, stage, dpiit = req.sector, req.stage, req.dpiit_recognized
    if req.startup_id:
        profile = data_loader.get_startup_by_id(req.startup_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Startup '{req.startup_id}' not found")
        sector = sector or profile["sector"]
        stage = stage or profile["stage"]
        dpiit = dpiit or profile["dpiit_recognized"]

    try:
        raw_matches = match_grants_for_startup(
            startup_id=req.startup_id,
            sector=sector,
            stage=stage,
            dpiit_recognized=dpiit,
            min_score=req.min_score,
            max_results=req.max_results,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    matches = [
        GrantMatch(
            **{k: v for k, v in m.items() if k != "score_breakdown"},
            score_breakdown=ScoreBreakdown(**m["score_breakdown"]),
        )
        for m in raw_matches
    ]

    return MatchResponse(
        startup_id=req.startup_id,
        sector=sector,
        stage=stage,
        dpiit_recognized=dpiit,
        matches=matches,
        total_matches=len(matches),
    )


# ─────────────────────────────────────────────────────────────────────────────
# AI Proposal Generation (IBM Granite)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/proposal", response_model=ProposalResponse, tags=["AI Generation"])
async def generate_proposal_endpoint(req: ProposalRequest):
    """Generate a tailored grant application draft using IBM Granite."""
    startup = data_loader.get_startup_by_id(req.startup_id)
    if not startup:
        raise HTTPException(status_code=404, detail=f"Startup '{req.startup_id}' not found")
    grant = data_loader.get_grant_by_id(req.grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail=f"Grant '{req.grant_id}' not found")

    proposal_text = generate_proposal(startup, grant)

    return ProposalResponse(
        startup_id=req.startup_id,
        grant_id=req.grant_id,
        grant_name=grant["grant_name"],
        company_name=startup["company_name"],
        proposal_text=proposal_text,
        model_used=settings.GRANITE_MODEL_ID,
    )


@app.post("/api/eligibility", response_model=EligibilityResponse, tags=["AI Generation"])
async def eligibility_analysis(req: EligibilityRequest):
    """Analyse whether a startup qualifies for a specific grant (IBM Granite)."""
    startup = data_loader.get_startup_by_id(req.startup_id)
    if not startup:
        raise HTTPException(status_code=404, detail=f"Startup '{req.startup_id}' not found")
    grant = data_loader.get_grant_by_id(req.grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail=f"Grant '{req.grant_id}' not found")

    analysis = generate_eligibility_analysis(startup, grant)

    return EligibilityResponse(
        startup_id=req.startup_id,
        grant_id=req.grant_id,
        analysis=analysis,
        model_used=settings.GRANITE_MODEL_ID,
    )


@app.get(
    "/api/grants/{grant_id}/summary",
    response_model=GrantSummaryResponse,
    tags=["AI Generation"],
)
async def grant_summary(grant_id: str):
    """Get a plain-language AI summary of a grant scheme."""
    grant = data_loader.get_grant_by_id(grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail=f"Grant '{grant_id}' not found")
    summary = generate_grant_summary(grant)
    return GrantSummaryResponse(
        grant_id=grant_id,
        grant_name=grant["grant_name"],
        summary=summary,
        model_used=settings.GRANITE_MODEL_ID,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Statistics
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/statistics", response_model=StatisticsResponse, tags=["Analytics"])
async def statistics():
    """Dashboard statistics across both datasets."""
    grant_stats = get_statistics()
    df = data_loader.get_startups_df()
    stage_counts = df["stage"].value_counts().to_dict()
    sector_counts = df["sector"].value_counts().to_dict()
    return StatisticsResponse(
        total_grants=grant_stats["total_grants"],
        total_startups=len(df),
        total_max_funding_inr=grant_stats["total_max_funding_inr"],
        offering_bodies=grant_stats["offering_bodies"],
        sectors_covered=grant_stats["sectors_covered"],
        stages_in_dataset=list(stage_counts.keys()),
        top_sectors={k: int(v) for k, v in list(sector_counts.items())[:8]},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Dev runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
