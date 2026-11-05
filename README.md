# 🔬 AI Grant & Funding Finder for Startups
### Problem Statement #18 · IBM Granite + watsonx.ai

> An end-to-end AI system that matches Indian startups with relevant government grant schemes and generates tailored application proposals using **IBM Granite** on **IBM watsonx.ai (Cloud Lite)**.

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Datasets](#datasets)
4. [Tech Stack](#tech-stack)
5. [Quick Start](#quick-start)
6. [Environment Variables (.env)](#environment-variables)
7. [API Reference](#api-reference)
8. [Matching Engine](#matching-engine)
9. [IBM Granite Integration](#ibm-granite-integration)
10. [Project Structure](#project-structure)

---

## Overview

Funding opportunities for startups are scattered across government portals with varying formats, eligibility criteria, and deadlines. This project solves that by:

- **Aggregating** 15 curated grant schemes (`grant_schemes_15.json`)
- **Profiling** 80 Indian startups (`startup_profiles_80.csv`) across 10 sectors
- **Matching** startups to relevant grants using a multi-signal scoring engine
- **Generating** personalised application drafts via **IBM Granite 13B Instruct**
- **Analysing** eligibility with AI-powered explanations
- Serving everything through a **FastAPI REST API** + browser UI

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser UI (/)                       │
│            static/index.html  (Vanilla JS)              │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/JSON
┌────────────────────▼────────────────────────────────────┐
│              FastAPI Backend  (main.py)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │data_loader│  │ matcher  │  │   granite_client     │  │
│  │(JSON+CSV) │  │(scoring) │  │ (IBM watsonx.ai SDK) │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │  IBM watsonx.ai     │
          │  (Cloud Lite)       │
          │  granite-13b-       │
          │  instruct-v2        │
          └─────────────────────┘
```

---

## Datasets

| File | Records | Description |
|------|---------|-------------|
| `grant_schemes_15.json` | 15 | Government grant schemes with eligibility, funding, deadlines |
| `startup_profiles_80.csv` | 80 | Startup profiles: sector, stage, DPIIT status, tech focus, revenue |

### Grant Scheme Fields
| Field | Type | Example |
|-------|------|---------|
| `grant_id` | string | `GR001` |
| `grant_name` | string | `Startup India Seed Fund Scheme` |
| `offering_body` | string | `DPIIT` |
| `max_funding_amount_inr` | int | `5000000` |
| `eligible_stages` | list | `["Pre-seed", "Seed"]` |
| `eligible_sectors` | list | `["DeepTech/AI", "FinTech"]` |
| `min_dpiit_recognized` | string | `Yes` / `Any` |
| `key_requirements` | string | Free text |
| `application_deadline` | string | `2027-05-27` / `Open Year-Round` |

### Startup Profile Fields
| Field | Type | Example |
|-------|------|---------|
| `startup_id` | string | `ST014` |
| `company_name` | string | `DeepTech AlphaTech_Corp_14` |
| `sector` | string | `DeepTech/AI` |
| `stage` | string | `Seed` |
| `city` | string | `Ahmedabad` |
| `state` | string | `Gujarat` |
| `dpiit_recognized` | string | `Yes` / `No` |
| `tech_focus` | string | Free text description |
| `annual_revenue_inr` | int | `20539044` |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI / LLM | **IBM Granite 13B Instruct v2** via IBM watsonx.ai |
| Cloud | **IBM Cloud Lite** (free tier) |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Matching | Custom multi-signal scoring (NumPy) |
| Data | Pandas (CSV), JSON |
| Frontend | Vanilla HTML5 / CSS3 / JavaScript |
| Config | python-dotenv |

---

## Quick Start

### 1. Clone / open the project
```bash
cd PS-18
```

### 2. Create a virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
# Copy the example env file
copy .env.example .env      # Windows
cp .env.example .env        # Linux/Mac

# Edit .env and fill in your IBM credentials
notepad .env
```

### 5. Run the server
```bash
python main.py
```

### 6. Open the UI
```
http://localhost:8000
```

Interactive API docs: `http://localhost:8000/docs`

---

## Environment Variables

Copy `.env.example` → `.env` and configure:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `IBM_API_KEY` | ✅ | — | IBM Cloud API key |
| `IBM_PROJECT_ID` | ✅ | — | watsonx.ai project ID |
| `IBM_REGION` | | `us-south` | IBM Cloud region |
| `IBM_WML_URL` | | `https://us-south.ml.cloud.ibm.com` | WML endpoint |
| `GRANITE_MODEL_ID` | | `ibm/granite-13b-instruct-v2` | Model ID |
| `GRANITE_MAX_NEW_TOKENS` | | `1024` | Max tokens to generate |
| `GRANITE_TEMPERATURE` | | `0.7` | Generation temperature |
| `GRANT_SCHEMES_PATH` | | `grant_schemes_15.json` | Dataset path |
| `STARTUP_PROFILES_PATH` | | `startup_profiles_80.csv` | Dataset path |
| `PROPOSAL_BACKEND` | | `ibm_granite` | `ibm_granite` or `mock` |
| `MIN_MATCH_SCORE` | | `0.3` | Minimum match threshold |
| `MAX_MATCHES` | | `10` | Max results per query |

> **Demo mode**: Set `PROPOSAL_BACKEND=mock` to run without IBM credentials — all AI outputs will be templated fallbacks.

---

## API Reference

### `GET /api/startups`
List startup profiles. Query params: `sector`, `stage`, `dpiit`

### `GET /api/startups/{startup_id}`
Get a single startup profile by ID (e.g., `ST014`)

### `GET /api/grants`
List all 15 grant schemes

### `GET /api/grants/{grant_id}`
Get a grant. Add `?summarize=true` to include an AI plain-language summary.

### `GET /api/grants/{grant_id}/summary`
AI plain-language summary of a grant (IBM Granite)

### `POST /api/match`
Match grants to a startup. Request body:
```json
{
  "startup_id": "ST014",
  "min_score": 0.3,
  "max_results": 10
}
```
Or ad-hoc (without a startup ID):
```json
{
  "sector": "DeepTech/AI",
  "stage": "Seed",
  "dpiit_recognized": "Yes"
}
```

### `POST /api/proposal`
Generate grant application draft (IBM Granite):
```json
{
  "startup_id": "ST014",
  "grant_id": "GR002"
}
```

### `POST /api/eligibility`
AI eligibility analysis:
```json
{
  "startup_id": "ST006",
  "grant_id": "GR001"
}
```

### `GET /api/statistics`
Dashboard statistics

### `GET /health`
System health check

---

## Matching Engine

The `matcher.py` scoring engine computes a weighted score across five signals:

| Signal | Weight | Logic |
|--------|--------|-------|
| **Stage Match** | 35% | 1.0 if startup stage ∈ grant's eligible_stages |
| **Sector Match** | 35% | 1.0 exact · 0.8 if grant accepts "Any" |
| **DPIIT Compliance** | 15% | Must meet grant's DPIIT requirement |
| **Deadline Freshness** | 10% | "Open Year-Round" = 1.0; future dates = 0.5–1.0; past = 0.0 |
| **Funding Relevance** | 5% | Log-normalised max funding amount |

Grants with `total_score < MIN_MATCH_SCORE` are filtered out.

---

## IBM Granite Integration

`granite_client.py` handles all IBM Granite interactions:

- **Lazy initialisation** — model is created on first call, reused thereafter
- **Retry logic** — `tenacity` retries up to 3× with exponential back-off
- **Three prompt types**: proposal, eligibility analysis, plain-language summary
- **Mock backend** — deterministic offline fallback (set `PROPOSAL_BACKEND=mock`)

Model: `ibm/granite-13b-instruct-v2`  
Platform: IBM watsonx.ai (Cloud Lite)  
SDK: `ibm-watsonx-ai`

---

## Project Structure

```
PS-18/
├── main.py                  # FastAPI app + all API routes
├── config.py                # Centralised settings (env-driven)
├── data_loader.py           # Dataset loading & in-memory indexing
├── matcher.py               # Multi-signal grant matching engine
├── granite_client.py        # IBM Granite / watsonx.ai integration
├── schemas.py               # Pydantic request/response models
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template (copy → .env)
├── grant_schemes_15.json    # 15 grant schemes dataset
├── startup_profiles_80.csv  # 80 startup profiles dataset
└── static/
    └── index.html           # Full-featured browser UI
```

---

## Getting IBM Cloud Lite Credentials

1. Sign up at [cloud.ibm.com](https://cloud.ibm.com) (free Lite account)
2. Create a **Watson Machine Learning** service instance (Lite plan)
3. Create a **watsonx.ai** project
4. Generate an **API key** from IAM → Manage → Access → API Keys
5. Copy the **Project ID** from your watsonx.ai project settings
6. Set `IBM_API_KEY` and `IBM_PROJECT_ID` in your `.env` file

---

*PS-18 · AI Grant & Funding Finder for Startups · Built with IBM Granite + watsonx.ai*
