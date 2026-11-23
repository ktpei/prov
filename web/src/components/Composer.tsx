import { useState } from "react";

type Props = {
  busy: boolean;
  unavailable?: boolean;
  context: { sheet: string; range: string } | null;
  hasHistory: boolean;
  onAsk: (question: string) => Promise<boolean>;
  onClearContext: () => void;
};

export function Composer({ busy, unavailable, context, hasHistory, onAsk, onClearContext }: Props) {
  const [text, setText] = useState("");
  const submit = async () => {
    const question = text.trim();
    if (!question || busy || unavailable) return;
    if (await onAsk(question)) setText("");
  };
  return (
    <form
      className="border-t border-rule bg-surface px-4 py-3"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      {context && (
        <div className="mb-2 flex items-center gap-2 text-xs">
          <span className="rounded border border-highlight bg-highlight-soft px-1.5 py-0.5">
            Workbook range {context.sheet}!{context.range} attached
          </span>
          <button type="button" onClick={onClearContext} className="text-ink-faint underline hover:text-ink">
            Remove
          </button>
        </div>
      )}
      <div className="flex items-end gap-2">
        <label htmlFor="question" className="sr-only">
          Question
        </label>
        <textarea
          id="question"
          rows={2}
          maxLength={4000}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
          placeholder={hasHistory ? "Ask a follow-up" : "Ask about a company, metric and period"}
          className="min-h-[44px] flex-1 resize-y rounded-md border border-rule bg-surface px-3 py-2 placeholder:text-ink-faint focus:border-ledger focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy || unavailable || !text.trim()}
          className="h-[44px] rounded-md bg-ledger px-4 font-medium text-white disabled:opacity-40"
        >
          {busy ? "Researching" : "Ask"}
        </button>
      </div>
      <p className="mt-1 text-xs text-ink-faint">Enter to send · Shift+Enter for a new line</p>
    </form>
  );
}
