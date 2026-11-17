"""Run the browser MVP: uv run python -m provenance.web [--replay] [--port 8765]."""

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_env(path):
    """Load KEY=VALUE lines without overriding variables already set."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)


def main():
    parser = argparse.ArgumentParser(description="Provenance research chat (local web app)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--replay", action="store_true", help="Default to labeled scripted replay (no spend)"
    )
    args = parser.parse_args()
    load_env(ROOT / ".env")
    import uvicorn

    from provenance.web.app import create_app

    print(f"Provenance research chat → http://{args.host}:{args.port}")
    uvicorn.run(create_app(replay=args.replay), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
