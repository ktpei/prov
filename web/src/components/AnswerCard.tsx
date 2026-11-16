import type { Citation, Selection, TurnView } from "../types";
import { explainReason, formatUnit, formatValue, humanizeKey, money } from "../format";
import { CitationChip } from "./CitationChip";

type Props = {
  turn: TurnView;
  titles: Record<string, string>;
  selection: Selection | null;
  onCite: (citation: Citation) => void;
  onShowActivity: () => void;
  onShowChanges: () => void;
};

function Metrics({ turn }: { turn: TurnView }) {
  const m = turn.metrics;
  if (!m) return null;
  const stats = [
    [`${m.latency_seconds.toFixed(1)} s`, "time"],
    [`${m.model_calls}`, m.model_calls === 1 ? "model step" : "model steps"],
    [`${m.tool_calls}`, m.tool_calls === 1 ? "tool call" : "tool calls"],
    [`${m.tool_errors}`, m.tool_errors === 1 ? "tool error" : "tool errors"],
    [`${(m.input_tokens + m.output_tokens).toLocaleString()}`, "tokens"],
    [m.cost_uncertain ? `≤ ${money(m.accounted_cost_usd)}` : money(m.accounted_cost_usd), "cost"],
  ];
  return (
    <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1 border-t border-rule pt-2 text-xs text-ink-faint">
      {stats.map(([value, label]) => (
        <div key={label} className="flex gap-1">
          <dt className="sr-only">{label}</dt>
          <dd className="tabular text-ink-soft">{value}</dd>
          <span aria-hidden>{label}</span>
        </div>
      ))}
    </dl>
  );
}

export function AnswerCard({ turn, titles, selection, onCite, onShowActivity, onShowChanges }: Props) {
  const replay = turn.mode === "offline_replay";
  const answer = turn.answer;
  const active = (c: Citation) =>
    !!selection && selection.citation.source_id === c.source_id && selection.citation.locator === c.locator;

  if (turn.status !== "completed" || !answer) {
    return (
      <div className="rounded-lg border border-rust/40 bg-rust-soft px-4 py-3">
        <p className="font-medium text-rust">No validated answer</p>
        <p className="mt-1 text-sm text-ink">{explainReason(turn.stop_reason)}</p>
        <p className="mt-1 text-sm text-ink-soft">
          Nothing unverified is shown. Try a narrower question, or{" "}
          <button type="button" className="underline" onClick={onShowActivity}>
            review what the agent read
          </button>
          .
        </p>
        <Metrics turn={turn} />
      </div>
    );
  }

  return (
    <div className={`rounded-lg border bg-surface px-4 py-3 ${answer.answerable ? "border-rule" : "border-ink-faint/40"}`}>
      <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs">
        {answer.answerable ? (
          <span className="rounded bg-ledger-soft px-1.5 py-0.5 text-ledger">Cited answer</span>
        ) : (
          <span className="rounded bg-chrome px-1.5 py-0.5 text-ink-soft">Not answerable from this evidence</span>
        )}
        {replay && (
          <span className="rounded bg-replay-soft px-1.5 py-0.5 text-replay">Scripted replay, no model call</span>
        )}
        {!replay && turn.model && <span className="text-ink-faint">{turn.model}</span>}
      </div>
      <p className="max-w-[72ch] whitespace-pre-wrap">{answer.answer}</p>

      {answer.claims.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-rule text-left text-xs text-ink-faint">
                <th className="py-1 pr-3 font-normal">Figure</th>
                <th className="py-1 pr-3 text-right font-normal">Value</th>
                <th className="py-1 pr-3 font-normal">Period</th>
                <th className="py-1 font-normal">Source</th>
              </tr>
            </thead>
            <tbody>
              {answer.claims.map((claim) => (
                <tr key={claim.key} className="border-b border-rule/60 align-top last:border-0">
                  <td className="py-1.5 pr-3">{humanizeKey(claim.key)}</td>
                  <td className="tabular py-1.5 pr-3 text-right font-medium whitespace-nowrap">
                    {formatValue(claim.value, claim.unit)}
                    {formatUnit(claim.unit) && (
                      <span className="ml-1 font-normal text-ink-faint">{formatUnit(claim.unit)}</span>
                    )}
                  </td>
                  <td className="tabular py-1.5 pr-3 whitespace-nowrap text-ink-soft">{claim.period}</td>
                  <td className="py-1.5">
                    <div className="flex flex-wrap gap-1">
                      {claim.citations.map((citation, index) => (
                        <CitationChip
                          key={index}
                          citation={citation}
                          titles={titles}
                          active={active(citation)}
                          onOpen={onCite}
                        />
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {turn.proposal_ids.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-highlight bg-highlight-soft px-3 py-2 text-sm">
          <span>
            {turn.proposal_ids.length === 1
              ? "1 proposed workbook change is waiting for your approval."
              : `${turn.proposal_ids.length} proposed workbook changes are waiting for your approval.`}{" "}
            Nothing has been written.
          </span>
          <button type="button" onClick={onShowChanges} className="rounded-md bg-ink px-2.5 py-1 text-white">
            Review changes
          </button>
        </div>
      )}
      <Metrics turn={turn} />
    </div>
  );
}
