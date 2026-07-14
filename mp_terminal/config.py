"""Configuration loaded from a mapping (Streamlit st.secrets) with env-var fallback.

No secrets are hardcoded. On Streamlit Community Cloud, set these under the app's Secrets
(see .streamlit/secrets.toml.example). Locally they can come from environment variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass
class Settings:
    data_source: str = "massive"              # "massive" (default) | "finnhub" | "schwab" | "mock"
    finnhub_api_key: str = ""
    massive_api_key: str = ""
    schwab_app_key: str = ""
    schwab_app_secret: str = ""
    schwab_redirect_uri: str = "https://mp-trading-terminal.streamlit.app"
    enable_order_entry: bool = False
    scan_refresh_seconds: int = 60
    price_min: float = 2.00
    price_max: float = 20.00
    priority_min: float = 3.00
    priority_max: float = 5.00


def load_settings(source: Optional[Mapping] = None) -> Settings:
    src = dict(source) if source else {}

    def get(key: str, default):
        # Accept both UPPER and lower keys from secrets; fall back to environment.
        return src.get(key.upper(), src.get(key, os.environ.get(key.upper(), default)))

    def as_bool(v) -> bool:
        return str(v).strip().lower() in {"1", "true", "yes", "on"}

    return Settings(
        data_source=get("data_source", "massive"),
        finnhub_api_key=get("finnhub_api_key", ""),
        massive_api_key=get("massive_api_key", ""),
        schwab_app_key=get("schwab_app_key", ""),
        schwab_app_secret=get("schwab_app_secret", ""),
        schwab_redirect_uri=get("schwab_redirect_uri", "https://mp-trading-terminal.streamlit.app"),
        enable_order_entry=as_bool(get("enable_order_entry", False)),
        scan_refresh_seconds=int(get("scan_refresh_seconds", 60)),
    )
