"""
data_loader.py — loads and indexes grant schemes and startup profiles
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# In-memory stores (populated once at startup)
# ─────────────────────────────────────────────────────────────────────────────
_grants: List[dict] = []
_startups: pd.DataFrame = pd.DataFrame()


def load_all() -> None:
    """Load both datasets into memory. Called once during app startup."""
    global _grants, _startups
    _grants = _load_grants()
    _startups = _load_startups()
    logger.info(
        "Datasets loaded — %d grant schemes, %d startup profiles",
        len(_grants),
        len(_startups),
    )


def _load_grants() -> List[dict]:
    path = Path(settings.GRANT_SCHEMES_PATH)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    logger.debug("Loaded %d grants from %s", len(data), path)
    return data


def _load_startups() -> pd.DataFrame:
    path = Path(settings.STARTUP_PROFILES_PATH)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    df = pd.read_csv(path, dtype=str)
    # Normalise numeric column
    df["annual_revenue_inr"] = pd.to_numeric(
        df["annual_revenue_inr"], errors="coerce"
    ).fillna(0)
    logger.debug("Loaded %d startups from %s", len(df), path)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Public accessors
# ─────────────────────────────────────────────────────────────────────────────

def get_grants() -> List[dict]:
    return list(_grants)


def get_startups_df() -> pd.DataFrame:
    return _startups.copy()


def get_startup_by_id(startup_id: str) -> Optional[dict]:
    df = _startups[_startups["startup_id"].str.upper() == startup_id.upper()]
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def get_grant_by_id(grant_id: str) -> Optional[dict]:
    for g in _grants:
        if g["grant_id"].upper() == grant_id.upper():
            return g
    return None
