"""
config.py — centralised settings loaded from environment / .env file
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (silently OK if it doesn't exist yet)
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)


class Settings:
    # IBM Cloud
    IBM_API_KEY: str = os.getenv("IBM_API_KEY", "")
    IBM_PROJECT_ID: str = os.getenv("IBM_PROJECT_ID", "")
    IBM_REGION: str = os.getenv("IBM_REGION", "us-south")
    IBM_WML_URL: str = os.getenv(
        "IBM_WML_URL", "https://us-south.ml.cloud.ibm.com"
    )

    # IBM Granite
    GRANITE_MODEL_ID: str = os.getenv(
        "GRANITE_MODEL_ID", "ibm/granite-13b-instruct-v2"
    )
    GRANITE_MAX_NEW_TOKENS: int = int(os.getenv("GRANITE_MAX_NEW_TOKENS", 1024))
    GRANITE_MIN_NEW_TOKENS: int = int(os.getenv("GRANITE_MIN_NEW_TOKENS", 50))
    GRANITE_TEMPERATURE: float = float(os.getenv("GRANITE_TEMPERATURE", 0.7))
    GRANITE_TOP_P: float = float(os.getenv("GRANITE_TOP_P", 0.9))
    GRANITE_TOP_K: int = int(os.getenv("GRANITE_TOP_K", 50))
    GRANITE_REPETITION_PENALTY: float = float(
        os.getenv("GRANITE_REPETITION_PENALTY", 1.1)
    )

    # Datasets
    GRANT_SCHEMES_PATH: str = os.getenv("GRANT_SCHEMES_PATH", "grant_schemes_15.json")
    STARTUP_PROFILES_PATH: str = os.getenv(
        "STARTUP_PROFILES_PATH", "startup_profiles_80.csv"
    )

    # App
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "True").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Matching
    MIN_MATCH_SCORE: float = float(os.getenv("MIN_MATCH_SCORE", 0.3))
    MAX_MATCHES: int = int(os.getenv("MAX_MATCHES", 10))

    # Proposal
    PROPOSAL_BACKEND: str = os.getenv("PROPOSAL_BACKEND", "ibm_granite")
    PROPOSAL_MAX_LENGTH: int = int(os.getenv("PROPOSAL_MAX_LENGTH", 800))


settings = Settings()
