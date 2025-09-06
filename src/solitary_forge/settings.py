from __future__ import annotations
import os


def _env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


TEST_MODE: bool = _env_bool("SOLITARY_FORGE_TEST_MODE", False)
NO_COLOR: bool = _env_bool("SOLITARY_FORGE_NO_COLOR", TEST_MODE)  # default: disabled unless test mode
