import { useEffect, useRef } from "react";
import type { Citation, Corpus, Progress, Selection, Session, TurnView } from "../types";
import { AnswerCard } from "./AnswerCard";

type Props = {
  corpus: Corpus;
  session: Session;
  progress: Record<string, Progress[]>;
  titles: Record<string, string>;
  selection: Selection | null;
  busy: boolean;
  onAsk: (question: string) => void;
  onCite: (citation: Citation) => void;
  onShowActivity: (turnId: string) => void;
  onShowChanges: () => void;
  onShowWorkbook: () => void;
};

function Running({ turn, events, onShowActivity }: { turn: TurnView; events: Progress[]; onShowActivity: () => void }) {
  const latest = events.filter(Boolean).at(-1);
  return (
    <div className="flex items-center gap-3 rounded-lg border border-rule bg-surface px-4 py-3 text-sm" aria-live="polite">
      <span className="pulse-dot h-2 w-2 rounded-full bg-ledger" aria-hidden />
      <span className="text-ink-soft">
        {latest ? latest.label : turn.mode === "offline_replay" ? "Starting scripted replay" : "Starting research"}
      </span>
      <button type="button" onClick={onShowActivity} className="ml-auto text-ledger underline">
        Watch activity
      </button>
    </div>
  );
}

export function Conversation(props: Props) {
  const { corpus, session, progress, busy, onAsk } = props;
  const end = useRef<HTMLDivElement>(null);
  const lastTurn = session.turns.at(-1);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [session.turns.length, lastTurn?.status]);

  if (session.turns.length === 0) {
    return (
      <div className="mx-auto max-w-[640px] px-1 py-6">
        <h1 className="text-[22px] font-semibold tracking-tight">{corpus.label}</h1>
        <p className="mt-1 text-ink-soft">{corpus.description}. Every figure in an answer links to the line it came from.</p>
        <ul className="mt-4 space-y-1 text-sm">
          {corpus.documents.map((doc) => (
            <li key={doc.id} className="flex gap-3">
              <span className="tabular w-[88px] shrink-0 text-ink-faint">{doc.published}</span>
              <span>{doc.title}</span>
            </li>
          ))}
        </ul>
        <h2 className="mt-6 text-sm font-medium text-ink-soft">Try a question</h2>
        <div className="mt-2 flex flex-col items-start gap-2">
          {corpus.starters.map((starter) => (
            <button
              key={starter}
              type="button"
              disabled={busy}
              onClick={() => onAsk(starter)}
              className="rounded-md border border-rule bg-surface px-3 py-2 text-left text-sm hover:border-ledger disabled:opacity-50"
            >
              {starter}
            </button>
          ))}
          {corpus.workbook_starters.length > 0 &&
            (session.workbook ? (
              corpus.workbook_starters.map((starter) => (
                <button
                  key={starter}
                  type="button"
                  disabled={busy}
                  onClick={() => onAsk(starter)}
                  className="rounded-md border border-highlight bg-highlight-soft px-3 py-2 text-left text-sm hover:border-ink-faint disabled:opacity-50"
                >
                  {starter}
                </button>
              ))
            ) : (
              <p className="text-sm text-ink-faint">
                Have a model to check?{" "}
                <button type="button" className="text-ledger underline" onClick={props.onShowWorkbook}>
                  Upload a workbook
                </button>{" "}
                and ask about its inputs.
              </p>
            ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5 py-4">
      {session.turns.map((turn) => (
        <section key={turn.id} aria-label={`Question ${turn.id}`} className="space-y-2">
          <div className="ml-auto max-w-[85%] rounded-lg bg-ink px-3.5 py-2 text-white">
            <p className="whitespace-pre-wrap">{turn.question}</p>
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
            <Running turn={turn} events={progress[turn.id] ?? []} onShowActivity={() => props.onShowActivity(turn.id)} />
          ) : (
            <AnswerCard
              turn={turn}
              titles={props.titles}
              selection={props.selection}
              onCite={props.onCite}
              onShowActivity={() => props.onShowActivity(turn.id)}
              onShowChanges={props.onShowChanges}
            />
          )}
        </section>
      ))}
      {session.workbook && !busy && (
        <div className="flex flex-col items-start gap-2">
          {corpus.workbook_starters
            .filter((starter) => !session.turns.some((turn) => turn.question === starter))
            .map((starter) => (
              <button
                key={starter}
                type="button"
                onClick={() => onAsk(starter)}
                className="rounded-md border border-highlight bg-highlight-soft px-3 py-2 text-left text-sm hover:border-ink-faint"
              >
                {starter}
              </button>
            ))}
        </div>
      )}
      <div ref={end} />
    </div>
  );
}
