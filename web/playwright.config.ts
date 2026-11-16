import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  use: {
    baseURL: "http://127.0.0.1:8799",
    viewport: { width: 1440, height: 900 },
    acceptDownloads: true,
  },
  webServer: {
    command: "uv run python -m provenance.web --replay --port 8799",
    cwd: "..",
    url: "http://127.0.0.1:8799/api/config",
    reuseExistingServer: false,
    timeout: 60_000,
    // Replay only: blank key keeps live calls off even when .env has one.
    env: { WEB_LEDGER: "runs/web/e2e-ledger.jsonl", OPENROUTER_API_KEY: "", WEB_ACCESS_CODE: "" },
  },
});
