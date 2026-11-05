"""
granite_client.py — IBM Granite / WatsonX integration

Supports two backends controlled by PROPOSAL_BACKEND env var:
  - "ibm_granite"  : live calls to IBM watsonx.ai via ibm-watsonx-ai SDK
  - "mock"         : deterministic offline fallback for demos / CI
"""
from __future__ import annotations

import logging
import os
import textwrap
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# IBM Granite live client (lazy-initialised)
# ─────────────────────────────────────────────────────────────────────────────

_model = None  # ibm_watsonx_ai Model instance


def _get_model():
    global _model
    if _model is not None:
        return _model
    try:
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai import Credentials

        credentials = Credentials(
            url=settings.IBM_WML_URL,
            api_key=settings.IBM_API_KEY,
        )
        params = {
            "max_new_tokens": settings.GRANITE_MAX_NEW_TOKENS,
            "min_new_tokens": settings.GRANITE_MIN_NEW_TOKENS,
            "temperature": settings.GRANITE_TEMPERATURE,
            "top_p": settings.GRANITE_TOP_P,
            "top_k": settings.GRANITE_TOP_K,
            "repetition_penalty": settings.GRANITE_REPETITION_PENALTY,
        }
        _model = ModelInference(
            model_id=settings.GRANITE_MODEL_ID,
            params=params,
            credentials=credentials,
            project_id=settings.IBM_PROJECT_ID,
        )
        logger.info("IBM Granite model initialised: %s", settings.GRANITE_MODEL_ID)
    except Exception as exc:
        logger.error("Failed to initialise IBM Granite model: %s", exc)
        raise
    return _model


# ─────────────────────────────────────────────────────────────────────────────
# Prompt templates
# ─────────────────────────────────────────────────────────────────────────────

_PROPOSAL_TEMPLATE = """You are an expert grant writer helping an Indian startup apply for a government grant.

### Startup Profile
- Company: {company_name}
- Sector: {sector}
- Stage: {stage}
- City: {city}, {state}
- DPIIT Recognised: {dpiit_recognized}
- Technology Focus: {tech_focus}

### Target Grant
- Grant: {grant_name}
- Offered by: {offering_body}
- Max Funding: ₹{max_funding_amount_inr:,}
- Eligibility Requirements: {key_requirements}
- Application Deadline: {application_deadline}

### Task
Write a concise, compelling grant application proposal (max {max_length} words) that:
1. Clearly states the startup's problem statement and solution
2. Highlights alignment with the grant's sectoral and stage requirements
3. Outlines expected milestones for the funded period
4. Explains the societal or economic impact
5. Closes with a strong call to action

Use formal, professional language. Do NOT invent facts beyond what is provided.

### Grant Application Draft:
"""

_ELIGIBILITY_TEMPLATE = """You are an expert in Indian government startup grants.

### Startup Profile
- Sector: {sector}
- Stage: {stage}
- DPIIT Recognised: {dpiit_recognized}
- Technology Focus: {tech_focus}

### Grant
- Grant: {grant_name}
- Offered by: {offering_body}
- Eligible Stages: {eligible_stages}
- Eligible Sectors: {eligible_sectors}
- DPIIT Required: {min_dpiit_recognized}
- Key Requirements: {key_requirements}

### Task
In 3-4 sentences, explain:
1. Whether this startup is eligible for this grant and why
2. What the startup must do to strengthen its application
3. Any red flags or disqualifying conditions

### Eligibility Analysis:
"""

_SUMMARY_TEMPLATE = """You are a startup advisor. Summarise the following grant opportunity in 2-3 sentences for a startup founder who is not familiar with government schemes.

### Grant
- Name: {grant_name}
- Offered by: {offering_body}
- Max Funding: ₹{max_funding_amount_inr:,}
- Eligible Stages: {eligible_stages}
- Eligible Sectors: {eligible_sectors}
- Key Requirements: {key_requirements}
- Deadline: {application_deadline}

### Plain-Language Summary:
"""


# ─────────────────────────────────────────────────────────────────────────────
# Mock backend
# ─────────────────────────────────────────────────────────────────────────────

def _mock_proposal(startup: dict, grant: dict) -> str:
    return textwrap.dedent(f"""
    **Draft Application — {grant['grant_name']}**

    To: {grant['offering_body']}

    We, {startup.get('company_name', 'our startup')}, a {startup.get('stage', 'early-stage')}
    startup operating in the {startup.get('sector', 'technology')} sector, hereby apply for
    the {grant['grant_name']} grant.

    Our solution — {startup.get('tech_focus', 'an innovative technology platform')} — directly
    addresses gaps in {startup.get('sector', 'the sector')} and aligns with your programme's
    thematic goals.

    We are DPIIT recognised ({startup.get('dpiit_recognized', 'Yes')}) and headquartered in
    {startup.get('city', 'India')}. We request ₹{grant.get('max_funding_amount_inr', 0):,}
    to accelerate product development, hire key talent, and achieve commercial milestones
    within 18 months.

    Proposed milestones:
    - Month 3 : MVP enhancement and beta rollout to 500 users
    - Month 9 : Revenue of ₹{int(grant.get('max_funding_amount_inr', 500000) * 0.2):,}
    - Month 18: Series next funding readiness with full product launch

    We look forward to partnering with {grant['offering_body']} to drive positive impact.

    Respectfully,
    {startup.get('company_name', 'Our Startup')} Team
    """).strip()


def _mock_eligibility(startup: dict, grant: dict) -> str:
    stage_ok = startup.get("stage") in grant.get("eligible_stages", [])
    sector_ok = (
        startup.get("sector") in grant.get("eligible_sectors", [])
        or "Any" in grant.get("eligible_sectors", [])
    )
    dpiit_ok = (
        grant.get("min_dpiit_recognized", "Any").lower() == "any"
        or startup.get("dpiit_recognized", "No").lower() == "yes"
    )
    flags = []
    if not stage_ok:
        flags.append(f"The startup's stage ({startup.get('stage')}) does not match the grant's eligible stages ({grant.get('eligible_stages')}).")
    if not sector_ok:
        flags.append(f"The startup's sector ({startup.get('sector')}) does not match the grant's sectors ({grant.get('eligible_sectors')}).")
    if not dpiit_ok:
        flags.append("This grant requires DPIIT recognition, which the startup currently lacks.")

    if not flags:
        return (
            f"{startup.get('company_name', 'This startup')} appears eligible for the "
            f"{grant['grant_name']}. The stage, sector, and DPIIT status all align. "
            "To strengthen the application, ensure all milestone documentation and innovation "
            "proof-points are clearly articulated in the submission."
        )
    return " ".join(flags) + " Address these gaps before applying."


def _mock_summary(grant: dict) -> str:
    return (
        f"The **{grant['grant_name']}** offered by {grant['offering_body']} provides up to "
        f"₹{grant.get('max_funding_amount_inr', 0):,} to startups at the "
        f"{', '.join(grant.get('eligible_stages', []))} stage in the "
        f"{', '.join(grant.get('eligible_sectors', []))} sector. "
        f"Key requirement: {grant.get('key_requirements', '')} "
        f"Deadline: {grant.get('application_deadline', 'N/A')}."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_proposal(startup: dict, grant: dict) -> str:
    """Generate a grant application draft using IBM Granite."""
    backend = os.environ.get("PROPOSAL_BACKEND", settings.PROPOSAL_BACKEND)
    if backend == "mock":
        return _mock_proposal(startup, grant)

    prompt = _PROPOSAL_TEMPLATE.format(
        company_name=startup.get("company_name", "N/A"),
        sector=startup.get("sector", "N/A"),
        stage=startup.get("stage", "N/A"),
        city=startup.get("city", "N/A"),
        state=startup.get("state", "N/A"),
        dpiit_recognized=startup.get("dpiit_recognized", "N/A"),
        tech_focus=startup.get("tech_focus", "N/A"),
        grant_name=grant["grant_name"],
        offering_body=grant["offering_body"],
        max_funding_amount_inr=grant.get("max_funding_amount_inr", 0),
        key_requirements=grant["key_requirements"],
        application_deadline=grant["application_deadline"],
        max_length=settings.PROPOSAL_MAX_LENGTH,
    )
    return _call_granite(prompt)


def generate_eligibility_analysis(startup: dict, grant: dict) -> str:
    """Analyse startup–grant eligibility using IBM Granite."""
    backend = os.environ.get("PROPOSAL_BACKEND", settings.PROPOSAL_BACKEND)
    if backend == "mock":
        return _mock_eligibility(startup, grant)

    prompt = _ELIGIBILITY_TEMPLATE.format(
        sector=startup.get("sector", "N/A"),
        stage=startup.get("stage", "N/A"),
        dpiit_recognized=startup.get("dpiit_recognized", "N/A"),
        tech_focus=startup.get("tech_focus", "N/A"),
        grant_name=grant["grant_name"],
        offering_body=grant["offering_body"],
        eligible_stages=", ".join(grant.get("eligible_stages", [])),
        eligible_sectors=", ".join(grant.get("eligible_sectors", [])),
        min_dpiit_recognized=grant.get("min_dpiit_recognized", "Any"),
        key_requirements=grant["key_requirements"],
    )
    return _call_granite(prompt)


def generate_grant_summary(grant: dict) -> str:
    """Generate a plain-language summary of a grant using IBM Granite."""
    backend = os.environ.get("PROPOSAL_BACKEND", settings.PROPOSAL_BACKEND)
    if backend == "mock":
        return _mock_summary(grant)

    prompt = _SUMMARY_TEMPLATE.format(
        grant_name=grant["grant_name"],
        offering_body=grant["offering_body"],
        max_funding_amount_inr=grant.get("max_funding_amount_inr", 0),
        eligible_stages=", ".join(grant.get("eligible_stages", [])),
        eligible_sectors=", ".join(grant.get("eligible_sectors", [])),
        key_requirements=grant["key_requirements"],
        application_deadline=grant["application_deadline"],
    )
    return _call_granite(prompt)


def _call_granite(prompt: str) -> str:
    """Internal: call the IBM Granite model with retry logic."""
    from tenacity import retry, stop_after_attempt, wait_exponential

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def _invoke(p: str) -> str:
        model = _get_model()
        response = model.generate_text(prompt=p)
        return response if isinstance(response, str) else str(response)

    try:
        return _invoke(prompt)
    except Exception as exc:
        logger.error("IBM Granite call failed: %s", exc)
        return f"[Generation error — please check IBM credentials. Detail: {exc}]"
