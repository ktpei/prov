import type { Citation, Progress, TurnView } from "../types";
import { explainReason, money, shortSource } from "../format";

type Props = {
  turn: TurnView | undefined;
  events: Progress[];
  titles: Record<string, string>;
  onOpenPassage: (citation: Citation) => void;
};

const ICONS: Record<Progress["kind"], string> = {
  started: "M3 8h10M9 4l4 4-4 4",
  model: "M8 2.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM6 8h4",
  search: "M7 3a4 4 0 100 8 4 4 0 000-8zM10 10l3.5 3.5",
  read: "M3 3.5h4.5a1.5 1.5 0 011.5 1.5v8a1 1 0 00-1-1H3zM13 3.5H9",
  workbook_read: "M2.5 2.5h11v11h-11zM2.5 6.5h11M6.5 2.5v11",
  proposal: "M3 13l1-3.5L11 2.5l2.5 2.5L6.5 12z",
  tool_error: "M8 3l6 10H2zM8 7v3",
  final_synthesis: "M3 8.5l3 3L13 4",
  answer_rejected: "M4 4l8 8M12 4l-8 8",
  finished: "M3 8.5l3 3L13 4",
};

function Row({ event, titles, onOpenPassage }: { event: Progress; titles: Record<string, string>; onOpenPassage: Props["onOpenPassage"] }) {
  const tone =
    event.kind === "tool_error" || event.kind === "answer_rejected"
      ? "text-rust"
      : event.kind === "proposal"
        ? "text-ink"
        : "text-ink-soft";
  const detail = event.detail as Record<string, unknown>;
  const hits = (detail.hits as { source_id: string; title: string; locator: string | null }[] | undefined) ?? [];
  const verb: Record<string, string> = {
    search: "Searched",
    read: "Read",
    workbook_read: "Read workbook",
    model: "",
    started: "",
    proposal: "",
    tool_error: "",
    final_synthesis: "",
    answer_rejected: "",
    finished: "",
  };
  return (
    <li className="activity-row grid grid-cols-[20px_minmax(0,1fr)_auto] gap-2 py-1.5">
      <svg aria-hidden viewBox="0 0 16 16" className={`mt-0.5 h-4 w-4 ${tone}`}>
        <path d={ICONS[event.kind]} fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="min-w-0 text-sm">
        <p className={tone}>
          {verb[event.kind] && <span className="text-ink-faint">{verb[event.kind]} </span>}
          {event.kind === "search" ? <span className="text-ink">“{event.label}”</span> : event.label}
          {event.kind === "read" && typeof detail.locator === "string" && (
            <button
              type="button"
              onClick={() => onOpenPassage({ source_id: String(detail.source_id), locator: String(detail.locator), quote: "" })}
              className="ml-1 text-ledger underline"
            >
              {String(detail.locator)}
            </button>
          )}
        </p>
        {event.kind === "search" && hits.length > 0 && (
          <ul className="mt-1 flex flex-wrap gap-1">
            {hits.map((hit) => (
              <li className="min-w-0 max-w-full" key={`${hit.source_id}-${hit.locator}`}>
                <button
                  type="button"
                  disabled={!hit.locator}
                  title={!hit.locator ? "Discovery result — evidence becomes available after the source is read" : undefined}
                  onClick={() => hit.locator && onOpenPassage({ source_id: hit.source_id, locator: hit.locator, quote: "" })}
                  className="max-w-full whitespace-normal text-left rounded border border-rule px-1.5 py-0.5 text-xs text-ink-soft hover:border-ledger"
                >
                  {shortSource(hit.source_id, titles[hit.source_id] ?? hit.title)} {hit.locator}
                </button>
              </li>
            ))}
          </ul>
        )}
        {(event.kind === "tool_error" || event.kind === "answer_rejected") && (
          <p className="mt-0.5 text-xs text-ink-soft">{String(detail.error ?? detail.reason ?? "")}</p>
        )}
        {event.kind === "model" && typeof detail.output_tokens === "number" && (
          <p className="tabular text-xs text-ink-faint">
            {Number(detail.input_tokens).toLocaleString()} in, {Number(detail.output_tokens).toLocaleString()} out
          </p>
        )}
      </div>
      <span className="tabular text-right text-xs text-ink-faint">
        {event.t.toFixed(1)} s
        {event.cost_usd !== null && event.cost_usd !== undefined && <span className="block">{money(event.cost_usd)}</span>}
      </span>
    </li>
  );
}

export function ActivityPanel({ turn, events, titles, onOpenPassage }: Props) {
  if (!turn) {
    return (
      <div className="p-6">
        <p className="font-medium">Activity</p>
        <p className="mt-1 max-w-[56ch] text-sm text-ink-soft">
          Each search, read, and model step appears here while the agent works, with time and running cost.
        </p>
      </div>
    );
  }
  const rows = events.filter(Boolean);
  return (
    <div className="activity-panel h-full overflow-y-auto px-5 py-4">
      <p className="text-sm text-ink-faint">Activity for</p>
      <p className="font-medium">{turn.question}</p>

      <ol className="mt-3 divide-y divide-rule/70" aria-live="polite">
        {rows.map((event, index) => (
          <Row key={index} event={event} titles={titles} onOpenPassage={onOpenPassage} />
        ))}
      </ol>
      {turn.status === "running" && (
        <p className="mt-2 flex items-center gap-2 text-sm text-ink-soft">
          <span className="pulse-dot h-2 w-2 rounded-full bg-ledger" aria-hidden /> Working
        </p>
      )}
      {turn.status !== "running" && turn.status !== "completed" && (
        <p className="mt-3 rounded-md bg-rust-soft px-3 py-2 text-sm text-rust">{explainReason(turn.stop_reason)}</p>
      )}
    </div>
  );
}
