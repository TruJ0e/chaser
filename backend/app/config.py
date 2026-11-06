from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    business_name: str = os.getenv("CHASER_BUSINESS_NAME", "TruJoe Digital")
    paypal_client_id: str = os.getenv("PAYPAL_CLIENT_ID", "")
    paypal_client_secret: str = os.getenv("PAYPAL_CLIENT_SECRET", "")
    paypal_sandbox: bool = env_bool("PAYPAL_SANDBOX", True)
    nebius_base_url: str = os.getenv("NEBIUS_BASE_URL", "")
    nebius_api_key: str = os.getenv("NEBIUS_API_KEY", "")
    nebius_model: str = os.getenv(
        "NEBIUS_MODEL", "meta-llama/Llama-3.3-70B-Instruct"
    )
    activity_log: Path = Path(
        os.getenv("CHASER_ACTIVITY_LOG", str(REPO_ROOT / "backend/data/activity.jsonl"))
    )


settings = Settings()
