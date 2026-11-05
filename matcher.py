"""
matcher.py — multi-signal grant matching engine

Signals used (with weights):
  1. Stage match          (35 %) — startup stage in grant's eligible_stages list
  2. Sector match         (35 %) — startup sector matches grant's eligible_sectors
  3. DPIIT compliance     (15 %) — startup DPIIT flag meets grant requirement
  4. Deadline freshness   (10 %) — grants closing sooner score lower
  5. Funding relevance    ( 5 %) — larger funding is better (log-normalised)
"""
from __future__ import annotations

import logging
import math
from datetime import date, datetime
from typing import List, Optional

from data_loader import get_grants, get_startup_by_id

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
STAGE_WEIGHT = 0.35
SECTOR_WEIGHT = 0.35
DPIIT_WEIGHT = 0.15
DEADLINE_WEIGHT = 0.10
FUNDING_WEIGHT = 0.05

MAX_FUNDING = 5_000_000  # cap for normalisation
DAYS_HORIZON = 365        # deadline scoring window


def _stage_score(startup_stage: str, grant_stages: List[str]) -> float:
    """1.0 if stage matches, 0.0 otherwise."""
    return 1.0 if startup_stage in grant_stages else 0.0


def _sector_score(startup_sector: str, grant_sectors: List[str]) -> float:
    """1.0 for exact match, 0.8 if grant accepts 'Any', 0.0 otherwise."""
    if startup_sector in grant_sectors:
        return 1.0
    if "Any" in grant_sectors:
        return 0.8
    return 0.0


def _dpiit_score(startup_dpiit: str, grant_dpiit_req: str) -> float:
    """
    'Any'  → always satisfied (1.0)
    'Yes'  → only DPIIT recognised startups qualify
    """
    if grant_dpiit_req.lower() == "any":
        return 1.0
    if grant_dpiit_req.lower() == "yes" and startup_dpiit.lower() == "yes":
        return 1.0
    return 0.0


def _deadline_score(deadline_str: str) -> float:
    """
    Open Year-Round → 1.0  (always available)
    Future date within horizon → 0.5–1.0 (further = better)
    Past date → 0.0
    """
    if deadline_str.lower().startswith("open"):
        return 1.0
    try:
        dl = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        today = date.today()
        if dl < today:
            return 0.0
        days_left = (dl - today).days
        return min(days_left / DAYS_HORIZON, 1.0)
    except ValueError:
        return 0.5


def _funding_score(amount: int) -> float:
    """Log-normalised funding amount → [0, 1]."""
    if amount <= 0:
        return 0.1  # non-monetary programme still has value
    return math.log1p(amount) / math.log1p(MAX_FUNDING)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def match_grants_for_startup(
    startup_id: Optional[str] = None,
    *,
    sector: Optional[str] = None,
    stage: Optional[str] = None,
    dpiit_recognized: Optional[str] = None,
    min_score: float = 0.3,
    max_results: int = 10,
) -> List[dict]:
    """
    Return ranked list of matching grants for the given startup.
    Either supply startup_id (looks up from dataset) or raw fields directly.
    """
    if startup_id:
        profile = get_startup_by_id(startup_id)
        if not profile:
            return []
        sector = profile.get("sector", sector)
        stage = profile.get("stage", stage)
        dpiit_recognized = profile.get("dpiit_recognized", dpiit_recognized)

    if not all([sector, stage, dpiit_recognized]):
        raise ValueError("sector, stage, and dpiit_recognized are required.")

    grants = get_grants()
    results = []

    for grant in grants:
        s_stage = _stage_score(stage, grant["eligible_stages"])
        s_sector = _sector_score(sector, grant["eligible_sectors"])
        s_dpiit = _dpiit_score(dpiit_recognized, grant["min_dpiit_recognized"])
        s_deadline = _deadline_score(grant["application_deadline"])
        s_funding = _funding_score(grant.get("max_funding_amount_inr", 0))

        total = (
            s_stage * STAGE_WEIGHT
            + s_sector * SECTOR_WEIGHT
            + s_dpiit * DPIIT_WEIGHT
            + s_deadline * DEADLINE_WEIGHT
            + s_funding * FUNDING_WEIGHT
        )

        if total >= min_score:
            results.append(
                {
                    "grant_id": grant["grant_id"],
                    "grant_name": grant["grant_name"],
                    "offering_body": grant["offering_body"],
                    "max_funding_amount_inr": grant.get("max_funding_amount_inr", 0),
                    "eligible_stages": grant["eligible_stages"],
                    "eligible_sectors": grant["eligible_sectors"],
                    "key_requirements": grant["key_requirements"],
                    "application_deadline": grant["application_deadline"],
                    "match_score": round(total, 4),
                    "score_breakdown": {
                        "stage": round(s_stage * STAGE_WEIGHT, 4),
                        "sector": round(s_sector * SECTOR_WEIGHT, 4),
                        "dpiit": round(s_dpiit * DPIIT_WEIGHT, 4),
                        "deadline": round(s_deadline * DEADLINE_WEIGHT, 4),
                        "funding": round(s_funding * FUNDING_WEIGHT, 4),
                    },
                }
            )

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:max_results]


def get_statistics() -> dict:
    """Aggregate statistics across the grant catalogue."""
    grants = get_grants()
    total_funding = sum(g.get("max_funding_amount_inr", 0) for g in grants)
    bodies = list({g["offering_body"] for g in grants})
    sectors: set = set()
    for g in grants:
        sectors.update(g["eligible_sectors"])
    return {
        "total_grants": len(grants),
        "total_max_funding_inr": total_funding,
        "offering_bodies": bodies,
        "sectors_covered": sorted(s for s in sectors if s != "Any"),
    }
