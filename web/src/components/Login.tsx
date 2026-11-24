import { useState } from "react";

type Props = { onSubmit: (code: string) => Promise<void> };

export function Login({ onSubmit }: Props) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  return (
    <div className="grid h-full place-items-center p-6">
      <form
        className="w-full max-w-[380px] rounded-lg border border-rule bg-surface p-6"
        onSubmit={async (event) => {
          event.preventDefault();
          setWorking(true);
          setError(null);
          try {
            await onSubmit(code);
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setWorking(false);
          }
        }}
      >
        <div className="flex items-center gap-2">
          <svg aria-hidden viewBox="0 0 32 32" className="h-6 w-6">
            <rect width="32" height="32" rx="6" fill="#1B2430" />
            <path d="M9 17l5 5 9-12" stroke="#F3E58A" strokeWidth="3.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <h1 className="text-[17px] font-semibold">Provenance Research</h1>
        </div>
        <p className="mt-3 text-sm text-ink-soft">Research uses a live model. Enter the access code you were given.</p>
        <label htmlFor="code" className="mt-4 block text-sm font-medium">
          Access code
        </label>
        <input
          id="code"
          type="password"
          autoComplete="current-password"
          autoFocus
          value={code}
          onChange={(event) => setCode(event.target.value)}
          className="mt-1 w-full rounded-md border border-rule px-3 py-2 focus:border-ledger focus:outline-none"
        />
        {error && (
          <p role="alert" className="mt-2 text-sm text-rust">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={!code.trim() || working}
          className="mt-4 w-full rounded-md bg-ledger py-2 font-medium text-white disabled:opacity-40"
        >
          {working ? "Checking" : "Open research"}
        </button>
      </form>
    </div>
  );
}
