import type { Config } from "../types";

export function Header({ config, busy, onNew }: { config: Config; busy: boolean; onNew: () => void }) {
  return (
    <header className="pane-header border-b border-rule bg-surface px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold">Provenance</span>
        <button onClick={onNew} disabled={busy} className="rounded border border-rule px-3 py-2 text-sm disabled:opacity-40">New chat</button>
      </div>
      <p role="status" className="mt-1 text-xs text-ink-soft">
        {config.live_available ? "Live research · Exa" : "Live research unavailable — check server configuration"}
      </p>
    </header>
  );
}
