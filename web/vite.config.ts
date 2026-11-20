import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { getHttpsServerOptions } from "office-addin-dev-certs";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(async ({ mode }) => ({
  plugins: [react(), tailwindcss()],
  server: { ...(mode === "excel" ? { host: "localhost", port: 3000, strictPort: true, https: await getHttpsServerOptions() } : {}), proxy: { "/api": "http://127.0.0.1:8765" } },
}));
