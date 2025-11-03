import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv, find_dotenv


@dataclass
class Settings:
    telegram_token: str
    db_url: str
    openchargemap_api_key: str | None
    plugshare_api_key: str | None
    default_search_radius_km: float
    max_results: int


def load_settings() -> Settings:
    # Load from .env if present; try current working dir, then project root, then src
    # 1) Use python-dotenv's search from CWD
    env_path = find_dotenv(usecwd=True)
    if not env_path:
        # 2) Try alongside this file's src directory
        src_root = Path(__file__).resolve().parents[1]
        candidate = src_root / ".env"
        if candidate.exists():
            env_path = str(candidate)
    if env_path:
        load_dotenv(env_path, override=False)

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    db_url = os.getenv("DATABASE_URL", "sqlite:///data/chargebot.db").strip()

    openchargemap_api_key = os.getenv("OCM_API_KEY", None)
    plugshare_api_key = os.getenv("PLUGSHARE_API_KEY", None)

    default_search_radius_km = float(os.getenv("DEFAULT_RADIUS_KM", "50"))
    max_results = int(os.getenv("MAX_RESULTS", "10"))

    return Settings(
        telegram_token=telegram_token,
        db_url=db_url,
        openchargemap_api_key=openchargemap_api_key,
        plugshare_api_key=plugshare_api_key,
        default_search_radius_km=default_search_radius_km,
        max_results=max_results,
    )


