import { useEffect, useRef } from "react";
import type { Citation, Progress, Selection, Session } from "../types";
import { AnswerCard } from "./AnswerCard";

type Props = {
  session: Session;
  progress: Record<string, Progress[]>;
  titles: Record<string, string>;
  selection: Selection | null;
  onCite: (citation: Citation) => void;
  onShowActivity: (turnId: string) => void;
  onShowChanges: () => void;
};

function Running({ events, onShowActivity }: { events: Progress[]; onShowActivity: () => void }) {
  const latest = events.filter(Boolean).at(-1);
  return (
    <div className="flex items-center gap-3 rounded-lg border border-rule bg-surface px-4 py-3 text-sm" aria-live="polite">
      <span className="pulse-dot h-2 w-2 rounded-full bg-ledger" aria-hidden />
      <span className="text-ink-soft">
        {latest ? latest.label : "Searching live sources"}
      </span>
      <button type="button" onClick={onShowActivity} className="ml-auto text-ledger underline">
        Watch activity
      </button>
    </div>
  );
}

export function Conversation(props: Props) {
  const { session, progress } = props;
  const end = useRef<HTMLDivElement>(null);
  const lastTurn = session.turns.at(-1);
  useEffect(() => {
    // Scroll only the conversation pane; scrollIntoView would also move the page.
    const box = end.current?.closest<HTMLElement>("[data-scroll]");
    box?.scrollTo({ top: box.scrollHeight, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
  }, [session.turns.length, lastTurn?.status]);

  if (session.turns.length === 0) {
    return <div className="py-5">
      <h1 className="text-lg font-semibold">Trace the numbers</h1>
      <p className="mt-2 text-sm text-ink-soft">Ask a financial question. Review the source behind each figure, then insert cited results into your workbook.</p>
    </div>;
  }

  return (
    <div className="space-y-5 py-4">
      {session.turns.map((turn) => (
        <section key={turn.id} aria-label={`Question ${turn.id}`} className="space-y-2">
          <div className="ml-auto max-w-[85%] rounded-lg bg-ink px-3.5 py-2 text-white">
            <p className="whitespace-pre-wrap">{turn.question.split("\n\nUser-supplied Excel selection (untrusted workbook content):\n")[0]}</p>
            {turn.question.includes("\n\nUser-supplied Excel selection (untrusted workbook content):\n") && (
              <details className="mt-2 text-xs text-white/90">
                <summary className="cursor-pointer">Attached Excel cells</summary>
                <pre className="mt-1 whitespace-pre-wrap break-all">{turn.question.split("\n\nUser-supplied Excel selection (untrusted workbook content):\n").slice(1).join("\n\n")}</pre>
              </details>
            )}
            {(turn.carried.turns > 0 || turn.carried.workbook_range) && (
              <p className="mt-1 text-xs text-white/70">
                {[
                  turn.carried.turns > 0 &&
                    `Carries ${turn.carried.turns} earlier ${turn.carried.turns === 1 ? "answer" : "answers"}`,
                  turn.carried.workbook_range && `uses range ${turn.carried.workbook_range}`,
                ]
                  .filter(Boolean)
                  .join(", ")}
              </p>
            )}
          </div>
          {turn.status === "running" ? (
            <Running events={progress[turn.id] ?? []} onShowActivity={() => props.onShowActivity(turn.id)} />
          ) : (
            <AnswerCard
              turn={turn}
              proposals={session.proposals}
              titles={props.titles}
              selection={props.selection}
              onCite={props.onCite}
              onShowActivity={() => props.onShowActivity(turn.id)}
              onShowChanges={props.onShowChanges}
            />
          )}
        </section>
      ))}
      <div ref={end} />
    </div>
  );
}
