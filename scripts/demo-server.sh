#!/bin/sh
# Serve the web MVP for a shared demo link: separate spend ledger and cap,
# access code from .env (WEB_ACCESS_CODE). Pair with: cloudflared tunnel --url http://127.0.0.1:8780
cd "$(dirname "$0")/.." || exit 1
export WEB_LEDGER="${WEB_LEDGER:-runs/web/demo-ledger.jsonl}"
export WEB_SPEND_CAP_USD="${WEB_SPEND_CAP_USD:-0.25}"
exec uv run python -m provenance.web --port "${PORT:-8780}"
