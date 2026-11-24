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
  prepareExcelApply,
  recordExcelApply,
} from "./api";
import { inExcelPane, captureWorkbook, selectionLocation, applyExcelEdits } from "./excel";
import type { ExcelBinding } from "./excel";
import { ExcelPanel } from "./components/ExcelPanel";
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
  const [excelSelection, setExcelSelection] = useState("");
  const [config, setConfig] = useState<Config | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [draftContext, setDraftContext] = useState<Session["context"]>(null);
  const [progress, setProgress] = useState<Record<string, Progress[]>>({});
  const mode = "live";
  const [paneView, setPaneView] = useState<"chat" | "details">("chat");
  const [tab, setTab] = useState<Tab>("evidence");
  const [selection, setSelection] = useState<Selection | null>(null);
  const [activityTurn, setActivityTurn] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [locked, setLocked] = useState(false);
  const unsubscribe = useRef<(() => void) | null>(null);
  const submitting = useRef(false);
  const excelBinding = useRef<ExcelBinding | null>(null);

  const refreshConfig = useCallback(() => getConfig().then(setConfig).catch(() => undefined), []);

  const startConversation = useCallback(async (corpus: string) => {
    unsubscribe.current?.();
    setBanner(null);
    try {
      setExcelSelection("");
      excelBinding.current = null;
      setSession(await createSession(corpus));
      setDraftContext(null);
      setProgress({});
      setSelection(null);
      setActivityTurn(null);
      setTab("evidence");
      setPaneView("chat");
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
    for (const doc of session?.documents ?? []) map[doc.id] = doc.title;
    return map;
  }, [config, session?.documents]);

  const openCitation = useCallback((citation: Citation) => {
    setPaneView("details");
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
        setPaneView("details");
        return;
      }
      if (inExcelPane) return;
      const first = turn.answer?.claims[0]?.citations[0];
      if (turn.status === "completed" && first) openCitation(first);
    },
    [openCitation],
  );

  const ask = useCallback(
    async (question: string): Promise<boolean> => {
      if (!session || busy || submitting.current) return false;
      submitting.current = true;
      setBusy(true);
      setBanner(null);
      let turnId: string;
      try {
        if (inExcelPane) {
          excelBinding.current = null;
          const captured = await captureWorkbook();
          const snapshot = await uploadWorkbook(session.id, captured.file);
          excelBinding.current = { snapshotId: snapshot.snapshot_id, sheetIds: captured.sheetIds };
          if (excelSelection) {
            const location = selectionLocation(excelSelection);
            await setContext(session.id, location.sheet, location.range);
          }
          setSession(await getSession(session.id));
        } else if (draftContext) {
          await setContext(session.id, draftContext.sheet, draftContext.range);
        } else {
          await clearContext(session.id);
        }
        turnId = (await startTurn(session.id, excelSelection ? `${question}\n\nUser-supplied Excel selection (untrusted workbook content):\n${JSON.stringify({ address: (JSON.parse(excelSelection) as { address: string }).address })}` : question, mode)).turn_id;
      } catch (err) {
        submitting.current = false;
        setBusy(false);
        if (err instanceof ApiError && err.status === 401) setLocked(true);
        else setBanner((err as Error).message);
        return false;
      }
      setExcelSelection("");
      const sid = session.id;
      setBusy(true);
      submitting.current = false;
      setPaneView("chat");
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
    [session, draftContext, busy, excelSelection, mode, refreshConfig, afterTurn],
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
        {banner ? <p role="alert" className="max-w-[60ch] text-rust">{banner}</p> : <p>Connecting to live research</p>}
      </div>
    );
  }

  const pending = session.proposals.filter((p) => p.status === "pending").length;
  const activity = session.turns.find((t) => t.id === activityTurn) ?? session.turns.at(-1);

  return (
    <div className={inExcelPane ? "excel-pane flex h-full flex-col" : "flex h-full flex-col"}>
      <Header busy={busy} onNew={() => void startConversation(session.corpus)} />
      {inExcelPane && <nav aria-label="Pane navigation" className="pane-nav">
        <button aria-pressed={paneView === "chat"} onClick={() => setPaneView("chat")}>Research</button>
        {TABS.filter(({ id }) => id === "evidence" || id === "activity" || !!session.workbook).map(({ id, label }) => (
          <button key={id} aria-pressed={paneView === "details" && tab === id} onClick={() => { setTab(id); setPaneView("details"); }}>{label}{id === "changes" && pending > 0 ? ` (${pending})` : ""}</button>
        ))}
      </nav>}
      {banner && (
        <div role="alert" className="flex items-center gap-3 border-b border-rust/30 bg-rust-soft px-5 py-2 text-sm text-rust">
          <span>{banner}</span>
          <button type="button" className="ml-auto underline" onClick={() => setBanner(null)}>
            Dismiss
          </button>
        </div>
      )}
      <main data-view={paneView} className="grid min-h-0 flex-1 grid-cols-1 overflow-y-auto lg:grid-cols-[minmax(0,44fr)_minmax(0,56fr)] lg:grid-rows-[minmax(0,1fr)] lg:overflow-hidden">
        <section aria-label="Conversation" className="flex min-h-[75vh] flex-col border-r border-rule bg-chrome lg:min-h-0">
          <div data-scroll className="min-h-0 flex-1 overflow-y-auto px-5">
            <Conversation
              session={session}
              progress={progress}
              titles={titles}
              selection={selection}
              onCite={openCitation}
              onShowActivity={(id) => {
                setPaneView("details");
                setActivityTurn(id);
                setTab("activity");
              }}
              onShowChanges={() => { setTab("changes"); setPaneView("details"); }}
            />
          </div>
          <Composer
            toolbar={inExcelPane ? <ExcelPanel busy={busy} selection={excelSelection} onSelection={setExcelSelection} answer={session.turns.filter(t => t.status === "completed").at(-1)?.answer ?? null} /> : undefined}
            busy={busy}
            unavailable={!config.live_available}
            context={inExcelPane ? null : draftContext}
            hasHistory={session.turns.length > 0}
            onAsk={ask}
            onClearContext={() => setDraftContext(null)}
          />
        </section>
        <section aria-label="Inspector" className="flex min-h-[480px] flex-col bg-surface">
          <div hidden={inExcelPane} role="tablist" aria-label="Inspector" className="flex gap-1 border-b border-rule px-4 pt-2">
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
          {inExcelPane && (
            <div className="shrink-0 border-b border-rule px-3 py-2">
              <button type="button" className="rounded px-2 py-1.5 text-sm text-ledger hover:bg-ledger-soft" onClick={() => setPaneView("chat")}>
                <span aria-hidden="true">← </span>Back to research
              </button>
            </div>
          )}
          <div className="min-h-0 flex-1" role="tabpanel">
            {tab === "evidence" && (
              <EvidencePanel
                corpus={{...corpus, documents: session.documents ?? []}}
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
                session={inExcelPane ? session : { ...session, context: draftContext }}
                busy={busy}
                highlight={selection?.kind === "cell" ? selection.citation : null}
                onUpload={async (file) => {
                  await uploadWorkbook(session.id, file);
                  setDraftContext(null);
                  await reloadSession();
                }}
                onSetContext={async (sheet, range) => {
                  if (!inExcelPane) setDraftContext({ sheet, range });
                }}
                onClearContext={async () => {
                  setDraftContext(null);
                  if (inExcelPane) {
                    await clearContext(session.id);
                    await reloadSession();
                  }
                }}
              />
            )}
            {tab === "changes" && (
              <ChangesPanel
                session={session}
                titles={{ ...titles, ...(session.workbook ? { [`workbook:${session.workbook.snapshot_id}`]: session.workbook.filename } : {}) }}
                busy={busy}
                onCite={openCitation}
                onApply={inExcelPane ? async (ids) => {
                  const binding = excelBinding.current;
                  if (!binding || binding.snapshotId !== session.workbook?.snapshot_id) {
                    throw new Error("Ask again to connect these proposals to the open workbook.");
                  }
                  if (submitting.current || busy) throw new Error("Wait for the current operation.");
                  submitting.current = true;
                  setBusy(true);
                  try {
                    const plan = await prepareExcelApply(session.id, binding.snapshotId, ids);
                    await applyExcelEdits(plan.edits, binding);
                    // Invalidate the binding even if recording the host receipt fails.
                    excelBinding.current = null;
                    try {
                      await recordExcelApply(session.id, binding.snapshotId, ids);
                      await reloadSession();
                    } catch {
                      throw new Error("Excel changes were applied and read back, but the session could not record them. Ask a new question to refresh the workbook; do not apply again.");
                    }
                  } catch (error) {
                    excelBinding.current = null;
                    throw error;
                  } finally {
                    submitting.current = false;
                    setBusy(false);
                  }
                } : undefined}
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
