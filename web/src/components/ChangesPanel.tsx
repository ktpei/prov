import { useEffect, useState } from "react";
import type { Citation, ExportRecord, Proposal, Session } from "../types";
import { CitationChip } from "./CitationChip";

type Props = {
  session: Session;
  titles: Record<string, string>;
  busy: boolean;
  onCite: (citation: Citation) => void;
  onExport: (ids: string[]) => Promise<ExportRecord>;
};

const STATUS: Record<Proposal["status"], { label: string; className: string }> = {
  pending: { label: "Awaiting approval", className: "bg-highlight-soft text-ink" },
  exported: { label: "In edited copy", className: "bg-ledger-soft text-ledger" },
  stale: { label: "Stale: workbook replaced", className: "bg-rust-soft text-rust" },
  superseded: { label: "Replaced by a newer proposal", className: "bg-chrome text-ink-faint" },
};

function content(value: number | string) {
  return typeof value === "number" ? value.toLocaleString("en-US", { maximumFractionDigits: 6 }) : value;
}

export function ChangesPanel({ session, titles, busy, onCite, onExport }: Props) {
  const proposals = session.proposals;
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    setChosen(new Set(proposals.filter((p) => p.status === "pending").map((p) => p.id)));
  }, [proposals.map((p) => `${p.id}:${p.status}`).join("|")]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!proposals.length) {
    return (
      <div className="p-6">
        <p className="font-medium">Proposed changes</p>
        <p className="mt-1 max-w-[56ch] text-sm text-ink-soft">
          When you ask whether a workbook input should change, the agent can propose cell edits backed by citations.
          They wait here for your approval; nothing is written before you approve.
        </p>
      </div>
    );
  }

  const approve = async () => {
    setWorking(true);
    setError(null);
    try {
      await onExport([...chosen]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setWorking(false);
    }
  };
  const latest = session.exports.filter((record) => record.snapshot_id === session.workbook?.snapshot_id).at(-1);
  const earlier = session.exports.filter((record) => record.id !== latest?.id);
  const blocked = !!session.workbook?.export_blockers?.length;

  return (
    <div className="h-full overflow-y-auto px-5 py-4">
      <p className="font-medium">Proposed changes</p>
      <p className="text-sm text-ink-soft">
        Approving creates a separate edited copy. Your uploaded file stays unchanged.
      </p>
      {blocked && <p role="status" className="mt-2 text-sm text-rust">Export is unavailable for this workbook: {session.workbook!.export_blockers.join(" ")}</p>}
      <ul className="mt-3 space-y-2">
        {proposals.map((proposal) => {
          const pending = proposal.status === "pending";
          const status = STATUS[proposal.status];
          return (
            <li key={proposal.id} className={`rounded-lg border bg-surface px-3 py-2.5 ${pending ? "border-rule" : "border-rule/60 opacity-80"}`}>
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  aria-label={`Approve change to ${proposal.sheet}!${proposal.cell}`}
                  className="mt-1 h-4 w-4 accent-ledger"
                  disabled={!pending || busy || blocked}
                  checked={chosen.has(proposal.id)}
                  onChange={(event) => {
                    const next = new Set(chosen);
                    if (event.target.checked) next.add(proposal.id);
                    else next.delete(proposal.id);
                    setChosen(next);
                  }}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="tabular font-medium">
                      {proposal.sheet}!{proposal.cell}
                    </span>
                    <span className="tabular text-sm">
                      <span className="text-ink-faint line-through">{proposal.old_formula ?? (proposal.old_display || "empty")}</span>
                      <span className="mx-1.5 text-ink-faint" aria-hidden>
                        to
                      </span>
                      <span className="font-medium text-ledger">{content(proposal.new_content)}</span>
                    </span>
                    <span className={`ml-auto rounded px-1.5 py-0.5 text-xs ${status.className}`}>{status.label}</span>
                  </div>
                  <p className="mt-1 text-sm text-ink-soft">{proposal.rationale}</p>
                  {(proposal.mode === "offline_replay" || (proposal.turn_status && proposal.turn_status !== "completed")) && (
                    <p className="mt-1 flex flex-wrap gap-1.5 text-xs">
                      {proposal.mode === "offline_replay" && (
                        <span className="rounded bg-replay-soft px-1.5 py-0.5 text-replay">From scripted replay, no model call</span>
                      )}
                      {proposal.turn_status && proposal.turn_status !== "completed" && (
                        <span className="rounded bg-rust-soft px-1.5 py-0.5 text-rust">
                          From a question that ended without a validated answer
                        </span>
                      )}
                    </p>
                  )}
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {proposal.citations.map((citation, index) => (
                      <CitationChip key={index} citation={citation} titles={titles} onOpen={onCite} />
                    ))}
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
      {proposals.some((p) => p.status === "pending") ? (
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={!chosen.size || working || busy || blocked}
          onClick={() => void approve()}
          className="rounded-md bg-ledger px-3.5 py-1.5 font-medium text-white disabled:opacity-40"
        >
          {working
            ? "Creating copy"
            : `Approve ${chosen.size} ${chosen.size === 1 ? "change" : "changes"} and create copy`}
        </button>
        {error && <p role="alert" className="text-sm text-rust">{error}</p>}
      </div>
      ) : (
        <p className="mt-3 text-sm text-ink-soft">
          {proposals.some((p) => p.status === "exported")
            ? "Approved changes are in the edited copy below."
            : "These proposals refer to a workbook you replaced. Ask again to get proposals for the current file."}
        </p>
      )}

      {latest && (
        <div className="mt-5 rounded-lg border border-ledger/40 bg-ledger-soft px-4 py-3">
          <p className="font-medium text-ledger">Edited copy ready</p>
          <p className="tabular mt-0.5 text-sm">{latest.filename}</p>
          <p className="mt-1 text-xs text-ink-soft">Includes every change approved so far for this uploaded snapshot.</p>
          <ul className="tabular mt-2 space-y-0.5 text-sm">
            {latest.changes.map((change) => (
              <li key={change.cell}>
                {change.cell}: {change.old || "empty"} to <span className="font-medium">{content(change.new)}</span>
                {change.generated_by?.startsWith("Scripted replay") && (
                  <span className="ml-2 text-xs text-replay">scripted replay</span>
                )}
              </li>
            ))}
          </ul>
          <a
            href={latest.download_url}
            download={latest.filename}
            className="mt-3 inline-block rounded-md bg-ink px-3 py-1.5 text-sm text-white"
          >
            Download edited copy
          </a>
          <p className="mt-2 text-sm text-ledger">Input changes verified · existing formulas preserved</p>
          <p className="mt-1 text-sm text-rust">Calculation pending — open in Excel to recalculate and review outputs.</p>
          <p className="mt-2 text-xs text-ink-soft">
            Each changed cell carries a comment with its source, and a Provenance log sheet lists every change and
            what generated it. This verifies file content, not financial correctness. The browser still shows your original snapshot; upload this copy to review another version.
          </p>
        </div>
      )}
      {earlier.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-ink-soft">Earlier copies ({earlier.length})</summary>
          <ul className="mt-2 space-y-1">
            {earlier
              .slice()
              .reverse()
              .map((record) => (
                <li key={record.id} className="flex flex-wrap items-baseline gap-2">
                  <a href={record.download_url} download={record.filename} className="tabular text-ledger underline">
                    {record.filename}
                  </a>
                  <span className="text-xs text-ink-faint">Snapshot {record.snapshot_id} · {record.changes.map((c) => c.cell).join(", ")}</span>
                </li>
              ))}
          </ul>
        </details>
      )}
    </div>
  );
}
