import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ApiError,
  clearContext,
  createExport,
  createSession,
  getAuth,
  getConfig,
  getSession,
  login,
  setContext,
  startTurn,
  streamTurn,
  uploadWorkbook,
  useDemoWorkbook,
} from "./api";
import { ActivityPanel } from "./components/ActivityPanel";
import { ChangesPanel } from "./components/ChangesPanel";
import { Composer } from "./components/Composer";
import { Conversation } from "./components/Conversation";
import { EvidencePanel } from "./components/EvidencePanel";
import { Header } from "./components/Header";
import { Login } from "./components/Login";
import { WorkbookPanel } from "./components/WorkbookPanel";
import type { Citation, Config, Progress, Selection, Session, Tab, TurnView } from "./types";

const TABS: { id: Tab; label: string }[] = [
  { id: "evidence", label: "Evidence" },
  { id: "activity", label: "Activity" },
  { id: "workbook", label: "Workbook" },
  { id: "changes", label: "Changes" },
];

export default function App() {
  const [config, setConfig] = useState<Config | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [progress, setProgress] = useState<Record<string, Progress[]>>({});
  const [mode, setMode] = useState<"live" | "replay">("live");
  const [tab, setTab] = useState<Tab>("evidence");
  const [selection, setSelection] = useState<Selection | null>(null);
  const [activityTurn, setActivityTurn] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [locked, setLocked] = useState(false);
  const unsubscribe = useRef<(() => void) | null>(null);
  const submitting = useRef(false);

  const refreshConfig = useCallback(() => getConfig().then(setConfig).catch(() => undefined), []);

  const startConversation = useCallback(async (corpus: string) => {
    unsubscribe.current?.();
    setBanner(null);
    try {
      setSession(await createSession(corpus));
      setProgress({});
      setSelection(null);
      setActivityTurn(null);
      setTab("evidence");
      setBusy(false);
    } catch (err) {
      setBanner((err as Error).message);
    }
  }, []);

  const boot = useCallback(() => {
    getAuth()
      .then((auth) => {
        if (auth.required && !auth.authenticated) {
          setLocked(true);
          return;
        }
        return getConfig().then((cfg) => {
        setLocked(false);
        setConfig(cfg);
        setMode(cfg.live_available && !cfg.replay ? "live" : "replay");
        return startConversation(cfg.corpora[0].id);
        });
      })
      .catch((err: Error) => {
        if (err instanceof ApiError && err.status === 401) setLocked(true);
        else setBanner(err.message);
      });
  }, [startConversation]);

  useEffect(() => {
    boot();
    return () => unsubscribe.current?.();
  }, [boot]);

  const corpus = config?.corpora.find((c) => c.id === session?.corpus) ?? null;
  const titles = useMemo(() => {
    const map: Record<string, string> = {};
    for (const c of config?.corpora ?? []) for (const doc of c.documents) map[doc.id] = doc.title;
    return map;
  }, [config]);

  const openCitation = useCallback((citation: Citation) => {
    if (citation.source_id.startsWith("workbook:")) {
      setSelection({ kind: "cell", citation });
      setTab("workbook");
    } else {
      setSelection({ kind: "source", citation });
      setTab("evidence");
    }
  }, []);

  const afterTurn = useCallback(
    (turn: TurnView) => {
      if (turn.status === "completed" && turn.proposal_ids.length) {
        setTab("changes");
        return;
      }
      const first = turn.answer?.claims[0]?.citations[0];
      if (turn.status === "completed" && first) openCitation(first);
    },
    [openCitation],
  );

  const ask = useCallback(
    async (question: string): Promise<boolean> => {
      if (!session || busy || submitting.current) return false;
      submitting.current = true;
      setBanner(null);
      let turnId: string;
      try {
        turnId = (await startTurn(session.id, question, mode)).turn_id;
      } catch (err) {
        submitting.current = false;
        if (err instanceof ApiError && err.status === 401) setLocked(true);
        else setBanner((err as Error).message);
        return false;
      }
      const sid = session.id;
      setBusy(true);
      submitting.current = false;
      setActivityTurn(turnId);
      setTab("activity");
      setProgress((current) => ({ ...current, [turnId]: [] }));
      getSession(sid).then(setSession).catch(() => undefined);
      unsubscribe.current = streamTurn(
        sid,
        turnId,
        (event, id) =>
          setProgress((current) => {
            const rows = [...(current[turnId] ?? [])];
            rows[id] = event;
            return { ...current, [turnId]: rows };
          }),
        async (turn) => {
          setBusy(false);
          try {
            setSession(await getSession(sid));
          } catch (err) {
            setBanner((err as Error).message);
          }
          void refreshConfig();
          afterTurn(turn);
        },
        (message) => {
          setBusy(false);
          setBanner(message);
          getSession(sid).then(setSession).catch(() => undefined);
        },
      );
      return true;
    },
    [session, busy, mode, refreshConfig, afterTurn],
  );

  const reloadSession = useCallback(async () => {
    if (session) setSession(await getSession(session.id));
  }, [session]);

  if (locked) {
    return (
      <Login
        onSubmit={async (code) => {
          await login(code);
          boot();
        }}
      />
    );
  }

  if (!config || !session || !corpus) {
    return (
      <div className="grid h-full place-items-center p-6 text-ink-soft">
        {banner ? <p role="alert" className="max-w-[60ch] text-rust">{banner}</p> : <p>Loading evidence sets</p>}
      </div>
    );
  }

  const pending = session.proposals.filter((p) => p.status === "pending").length;
  const activity = session.turns.find((t) => t.id === activityTurn) ?? session.turns.at(-1);

  return (
    <div className="flex h-full flex-col">
      <Header
        config={config}
        corpusId={session.corpus}
        mode={mode}
        busy={busy}
        onCorpus={(id) => void startConversation(id)}
        onMode={setMode}
        onNew={() => void startConversation(session.corpus)}
      />
      {banner && (
        <div role="alert" className="flex items-center gap-3 border-b border-rust/30 bg-rust-soft px-5 py-2 text-sm text-rust">
          <span>{banner}</span>
          <button type="button" className="ml-auto underline" onClick={() => setBanner(null)}>
            Dismiss
          </button>
        </div>
      )}
      <main className="grid min-h-0 flex-1 grid-cols-1 overflow-y-auto lg:grid-cols-[minmax(0,44fr)_minmax(0,56fr)] lg:grid-rows-[minmax(0,1fr)] lg:overflow-hidden">
        <section aria-label="Conversation" className="flex min-h-[75vh] flex-col border-r border-rule bg-chrome lg:min-h-0">
          <div data-scroll className="min-h-0 flex-1 overflow-y-auto px-5">
            <Conversation
              corpus={corpus}
              session={session}
              progress={progress}
              titles={titles}
              selection={selection}
              busy={busy}
              mode={mode}
              onAsk={(q) => void ask(q)}
              onCite={openCitation}
              onShowActivity={(id) => {
                setActivityTurn(id);
                setTab("activity");
              }}
              onShowChanges={() => setTab("changes")}
              onShowWorkbook={() => setTab("workbook")}
            />
          </div>
          <Composer
            busy={busy}
            context={session.context}
            hasHistory={session.turns.length > 0}
            onAsk={ask}
            onClearContext={() => void clearContext(session.id).then(reloadSession)}
          />
        </section>
        <section aria-label="Inspector" className="flex min-h-[480px] flex-col bg-surface">
          <div role="tablist" aria-label="Inspector" className="flex gap-1 border-b border-rule px-4 pt-2">
            {TABS.map(({ id, label }) => {
              const count = id === "changes" ? pending : 0;
              return (
                <button
                  key={id}
                  role="tab"
                  type="button"
                  aria-selected={tab === id}
                  onClick={() => setTab(id)}
                  className={`-mb-px flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm ${
                    tab === id ? "border-ink font-medium text-ink" : "border-transparent text-ink-soft hover:text-ink"
                  }`}
                >
                  {label}
                  {id === "workbook" && session.workbook && <span className="h-1.5 w-1.5 rounded-full bg-ledger" aria-label="workbook attached" />}
                  {count > 0 && (
                    <span className="tabular rounded-full bg-highlight px-1.5 text-xs text-ink" aria-label={`${count} pending`}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          <div className="min-h-0 flex-1" role="tabpanel">
            {tab === "evidence" && (
              <EvidencePanel
                corpus={corpus}
                citation={selection?.kind === "source" ? selection.citation : null}
                onOpenDocument={openCitation}
              />
            )}
            {tab === "activity" && (
              <ActivityPanel
                turn={activity}
                events={activity ? progress[activity.id] ?? [] : []}
                titles={titles}
                onOpenPassage={openCitation}
              />
            )}
            {tab === "workbook" && (
              <WorkbookPanel
                session={session}
                busy={busy}
                highlight={selection?.kind === "cell" ? selection.citation : null}
                onUpload={async (file) => {
                  await uploadWorkbook(session.id, file);
                  await reloadSession();
                }}
                onUseDemo={async () => {
                  await useDemoWorkbook(session.id);
                  await reloadSession();
                }}
                onSetContext={async (sheet, range) => {
                  await setContext(session.id, sheet, range);
                  await reloadSession();
                }}
                onClearContext={async () => {
                  await clearContext(session.id);
                  await reloadSession();
                }}
              />
            )}
            {tab === "changes" && (
              <ChangesPanel
                session={session}
                titles={{ ...titles, ...(session.workbook ? { [`workbook:${session.workbook.snapshot_id}`]: session.workbook.filename } : {}) }}
                busy={busy}
                onCite={openCitation}
                onExport={async (ids) => {
                  const record = await createExport(session.id, session.workbook!.snapshot_id, ids);
                  await reloadSession();
                  return record;
                }}
              />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
