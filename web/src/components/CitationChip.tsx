import type { Citation } from "../types";
import { shortSource } from "../format";

type Props = {
  citation: Citation;
  titles: Record<string, string>;
  active?: boolean;
  onOpen: (citation: Citation) => void;
};

export function CitationChip({ citation, titles, active, onOpen }: Props) {
  const isCell = citation.source_id.startsWith("workbook:");
  const locator = citation.locator.replace(/^L(\d+)-L?\1$/, "L$1");
  const label = isCell
    ? citation.locator
    : `${shortSource(citation.source_id, titles[citation.source_id])} ${locator}`;
  return (
    <button
      type="button"
      onClick={() => onOpen(citation)}
      title={`“${citation.quote}”`}
      aria-label={`Open source ${label}: ${citation.quote}`}
      className={`inline-flex items-center gap-1 rounded-[4px] border px-1.5 py-0.5 text-[12.5px] leading-tight whitespace-nowrap transition-colors ${
        active
          ? "border-ledger bg-ledger text-white"
          : "border-ledger/30 bg-ledger-soft text-ledger hover:border-ledger"
      }`}
    >
      <svg aria-hidden viewBox="0 0 12 12" className="h-3 w-3 shrink-0">
        {isCell ? (
          <path d="M1.5 1.5h9v9h-9zM1.5 5h9M5 1.5v9" fill="none" stroke="currentColor" strokeWidth="1.2" />
        ) : (
          <path d="M2 6.5l2.5 2.5L10 3" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        )}
      </svg>
      {label}
    </button>
  );
}
