import type { Config } from "../types";

type Props = {
  config: Config;
  corpusId: string;
  mode: "live" | "replay";
  busy: boolean;
  onCorpus: (id: string) => void;
  onMode: (mode: "live" | "replay") => void;
  onNew: () => void;
};

export function Header({ config, corpusId, mode, busy, onCorpus, onMode, onNew }: Props) {
  const corpus = config.corpora.find((c) => c.id === corpusId);
  const { total_usd, cap_usd } = config.spend;
  const used = Math.min(1, total_usd / cap_usd);
  return (
    <header className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-rule bg-surface px-5 py-2.5 2xl:gap-x-6">
      <div className="flex items-center gap-2">
        <svg aria-hidden viewBox="0 0 32 32" className="h-6 w-6">
          <rect width="32" height="32" rx="6" fill="#1B2430" />
          <path d="M9 17l5 5 9-12" stroke="#F3E58A" strokeWidth="3.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="text-[17px] font-semibold tracking-tight">Provenance Research</span>
      </div>

      <label className="flex items-center gap-2 text-sm text-ink-soft">
        <span className="sr-only 2xl:not-sr-only">Evidence</span>
        <select
          value={corpusId}
          disabled={busy}
          onChange={(event) => onCorpus(event.target.value)}
          className="rounded-md border border-rule bg-surface px-2 py-1 text-ink"
        >
          {config.corpora.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
      </label>
      {corpus && (
        <span className="text-sm text-ink-faint" title="Latest publication date in this evidence set">
          <span className="hidden 2xl:inline">Information cutoff </span>
          <span className="2xl:hidden">Cutoff </span>
          <span className="tabular text-ink-soft">{corpus.cutoff}</span>
        </span>
      )}

      <div className="ml-auto flex flex-wrap items-center gap-3 2xl:gap-4">
        <div role="radiogroup" aria-label="Answer mode" className="flex rounded-md border border-rule p-0.5 text-sm">
          {(["live", "replay"] as const).map((option) => {
            const disabled = busy || (option === "live" && !config.live_available);
            return (
              <button
                key={option}
                type="button"
                role="radio"
                aria-checked={mode === option}
                disabled={disabled}
                onClick={() => onMode(option)}
                title={
                  option === "live"
                    ? config.live_available
                      ? `Live model: ${config.model}`
                      : "Live model not configured (add OPENROUTER_API_KEY to .env)"
                    : "Scripted replay of recorded starter questions; no model call, no cost"
                }
                className={`rounded px-2.5 py-0.5 ${
                  mode === option
                    ? option === "live"
                      ? "bg-ledger text-white"
                      : "bg-replay text-white"
                    : "text-ink-soft hover:text-ink disabled:opacity-40"
                }`}
              >
                <span className="sm:hidden">{option === "live" ? "Live" : "Replay"}</span>
                <span className="hidden sm:inline">{option === "live" ? "Live model" : "Scripted replay"}</span>
              </button>
            );
          })}
        </div>
        <div className="min-w-[132px] text-xs text-ink-soft" title="Live model spend recorded in runs/web/cost-log.jsonl">
          <div className="tabular">
            Spent ${total_usd.toFixed(4)} of ${cap_usd.toFixed(2)}
          </div>
          <div className="mt-1 h-1 rounded bg-chrome">
            <div className="h-1 rounded bg-ledger" style={{ width: `${Math.max(2, used * 100)}%` }} />
          </div>
        </div>
        <button
          type="button"
          onClick={onNew}
          disabled={busy}
          className="rounded-md border border-rule px-3 py-1 text-sm hover:border-ink-faint disabled:opacity-40"
        >
          New conversation
        </button>
      </div>
    </header>
  );
}
