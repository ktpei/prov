import { useEffect, useRef } from "react";
import type { Citation, Progress, Selection, Session } from "../types";
import { inExcelPane } from "../excel";
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

function QuestionText({ question }: { question: string }) {
  const marker = "\n\nUser-supplied Excel selection (untrusted workbook content):\n";
  const boundary = inExcelPane ? question.indexOf(marker) : -1;
  if (boundary < 0) return <p className="whitespace-pre-wrap">{question}</p>;
  return <>
    <p className="whitespace-pre-wrap">{question.slice(0, boundary)}</p>
    <details className="mt-2 text-xs text-white/80">
      <summary className="cursor-pointer">Attached Excel cells</summary>
      <pre className="mt-2 whitespace-pre-wrap break-all">{question.slice(boundary + marker.length)}</pre>
    </details>
  </>;
}

export function Conversation(props: Props) {
  const { session, progress } = props;
  const end = useRef<HTMLDivElement>(null);
  const lastTurn = session.turns.at(-1);
  useEffect(() => {
    // Scroll only the conversation pane; scrollIntoView would also move the page.
    const box = end.current?.closest<HTMLElement>("[data-scroll]");
    box?.scrollTo({ top: box.scrollHeight, behavior: "smooth" });
  }, [session.turns.length, lastTurn?.status]);

  if (session.turns.length === 0) {
    return <div className="research-welcome py-5">
      <h1 className="text-lg font-semibold">Research your workbook</h1>
    </div>;
  }

  return (
    <div className="space-y-5 py-4">
      {session.turns.map((turn) => (
        <section key={turn.id} aria-label={`Question ${turn.id}`} className="space-y-2">
          <div className="ml-auto max-w-[85%] rounded-lg bg-ink px-3.5 py-2 text-white">
            <QuestionText question={turn.question} />
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
