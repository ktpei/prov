"""Load non-secret Excel/web settings and pass them to spawned research workers."""

import json
import os
from pathlib import Path

from provenance.controls import positive

CONFIG_PATH = Path(__file__).resolve().parents[2] / "research.config.json"
SETTINGS = {
    "model": "OPENROUTER_MODEL",
    "input_usd_per_million": "OPENROUTER_INPUT_USD_PER_MILLION",
    "output_usd_per_million": "OPENROUTER_OUTPUT_USD_PER_MILLION",
    "exa_max_request_usd": "EXA_MAX_REQUEST_USD",
    "max_turn_usd": "WEB_MAX_TURN_USD",
    "total_spend_usd": "WEB_SPEND_CAP_USD",
}


def load_settings(path=CONFIG_PATH):
    """Config is authoritative; credentials remain exclusively in the environment."""
    settings = json.loads(Path(path).read_text())
    if set(settings) != set(SETTINGS):
        raise ValueError("Research config must contain exactly: " + ", ".join(SETTINGS))
    if not isinstance(settings["model"], str) or not settings["model"].strip():
        raise ValueError("Research config model must be a nonempty string")
    for name in SETTINGS:
        if name != "model":
            positive(settings[name], name)
    # Existing CLI adapters and spawned workers consume environment variables.
    # Validate everything first, then bridge this single config into that interface.
    for name, env_name in SETTINGS.items():
        os.environ[env_name] = str(settings[name])
    return settings
