export function Header({ busy, onNew }: { busy: boolean; onNew: () => void }) {
  return (
    <header className="pane-header border-b border-rule bg-surface px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="brand-lockup flex items-center gap-2 font-semibold tracking-tight">
          <svg aria-hidden viewBox="0 0 32 32" className="h-6 w-6 shrink-0">
            <rect width="32" height="32" rx="6" fill="#1B2430" />
            <path d="M9 17l5 5 9-12" stroke="#F3E58A" strokeWidth="3.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Provenance
        </span>
        <button onClick={onNew} disabled={busy} className="rounded border border-rule px-3 py-2 text-sm disabled:opacity-40">New chat</button>
      </div>
    </header>
  );
}
