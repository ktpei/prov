import { useEffect, useRef, useState } from "react";
import { getSourceWindow, originalUrl } from "../api";
import { lineRange } from "../format";
import type { Citation, Corpus, SourceWindow } from "../types";

type Props = {
  corpus: Corpus;
  citation: Citation | null;
  onOpenDocument: (citation: Citation) => void;
};

function highlightQuote(text: string, quote: string) {
  const needle = quote.trim();
  if (!needle) return text;
  const index = text.indexOf(needle);
  if (index < 0) return text;
  return (
    <>
      {text.slice(0, index)}
      <mark className="quote">{needle}</mark>
      {text.slice(index + needle.length)}
    </>
  );
}

function locationLabel(location: SourceWindow["lines"][number]["location"]) {
  if (!location) return null;
  if (location.page) return `Original page ${location.page}`;
  if (location.section && location.section !== "Document") return `Section: ${location.section}`;
  return null;
}

export function EvidencePanel({ corpus, citation, onOpenDocument }: Props) {
  const [window, setWindow] = useState<SourceWindow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const target = useRef<HTMLLIElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const range = citation ? lineRange(citation.locator) : null;

  useEffect(() => {
    if (!citation || !range) return;
    let cancelled = false;
    const start = Math.max(1, range[0] - 10);
    const end = Math.min(start + 199, range[1] + 14);
    setError(null);
    setWindow(null);
    getSourceWindow(corpus.id, citation.source_id, start, end)
      .then((data) => !cancelled && setWindow(data))
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [corpus.id, citation?.source_id, citation?.locator]);

  useEffect(() => {
    if (box.current && target.current) {
      box.current.scrollTop = Math.max(0, target.current.offsetTop - box.current.clientHeight / 3);
    }
  }, [window]);

  if (!citation || !range) {
    return (
      <div className="p-6">
        <p className="font-medium">Evidence</p>
        <p className="mt-1 max-w-[56ch] text-sm text-ink-soft">
          Select a source tag in an answer to open the exact passage it cites, with the quoted text highlighted.
        </p>
        {corpus.documents.length > 0 && <h3 className="mt-5 text-sm font-medium text-ink-soft">Sources</h3>}
        <ul className="mt-2 space-y-1.5 text-sm">
          {corpus.documents.map((doc) => (
            <li key={doc.id}>
              <button
                type="button"
                className="text-left text-ledger underline-offset-2 hover:underline"
                onClick={() => onOpenDocument({ source_id: doc.id, locator: "L1-L40", quote: "" })}
              >
                {doc.title}
              </button>
              <span className="tabular ml-2 text-ink-faint">{doc.published}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  if (error) return <p role="alert" className="p-6 text-sm text-rust">{error}</p>;
  if (!window || window.id !== citation.source_id) return <p role="status" className="p-6 text-sm text-ink-faint">Loading passage</p>;

  const cited = window.lines.filter((line) => line.line >= range[0] && line.line <= range[1]);
  const location = cited
    .map((line) => locationLabel(line.location))
    .find((label) => label && label !== `Section: ${window.title}`);
  const page = cited.find((line) => line.location?.page)?.location?.page;
  const original = window.has_original
    ? `${originalUrl(corpus.id, window.id)}${window.original_type === "pdf" && page ? `#page=${page}` : ""}`
    : null;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-rule bg-surface px-5 py-3">
        <p className="font-medium leading-snug">{window.title}</p>
        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-soft">
          <span className="tabular">Published {window.published}</span>
          <span className="tabular">
            Lines {range[0]}–{range[1]} of {window.total_lines}
          </span>
          {location && <span>{location}</span>}
        </div>
        <div className="mt-2 flex flex-wrap gap-3 text-sm">
          {original && (
            <a href={original} target="_blank" rel="noreferrer" className="text-ledger underline">
              Open archived original{page && window.original_type === "pdf" ? ` at page ${page}` : ""}
            </a>
          )}
          <a href={window.url} target="_blank" rel="noreferrer" className="text-ledger underline">
            Public source
          </a>
        </div>
        {citation.quote && (
          <p className="mt-2 text-xs text-ink-faint">
            Quoted text: <span className="text-ink">“{citation.quote}”</span>
          </p>
        )}
      </div>
      <div ref={box} className="evidence-passage relative min-h-0 flex-1 overflow-y-auto bg-chrome p-4">
        <ol className="mx-auto max-w-[760px] rounded-sm border border-paper-rule bg-paper py-3 font-serif text-[14.5px] leading-[1.6] shadow-[0_1px_0_#d3d9e0]">
          {window.lines.map((line) => {
            const isCited = line.line >= range[0] && line.line <= range[1];
            return (
              <li
                key={line.line}
                ref={line.line === range[0] ? target : undefined}
                className={`grid grid-cols-[52px_1fr] gap-3 px-3 ${isCited ? "bg-highlight-soft" : ""}`}
              >
                <span
                  className={`tabular select-none pt-[1px] text-right font-sans text-xs ${isCited ? "font-semibold text-ink" : "text-ink-faint"}`}
                >
                  L{line.line}
                </span>
                <span className={`min-w-0 break-words ${isCited ? "text-ink" : "text-ink-soft"}`}>
                  {isCited ? highlightQuote(line.text, citation.quote) : line.text || " "}
                </span>
              </li>
            );
          })}
        </ol>
        <p className="mx-auto mt-2 max-w-[760px] text-xs text-ink-faint">{window.locator_note}</p>
      </div>
    </div>
  );
}
