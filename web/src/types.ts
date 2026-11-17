export type Citation = { source_id: string; locator: string; quote: string };

export type Claim = {
  key: string;
  value: number | string;
  unit: string;
  period: string;
  citations: Citation[];
};

export type Answer = { answerable: boolean; answer: string; claims: Claim[] };

export type Metrics = {
  model_calls: number;
  answer_retries: number;
  tool_calls: number;
  tool_errors: number;
  tool_error_rate: number | null;
  input_tokens: number;
  output_tokens: number;
  latency_seconds: number;
  accounted_cost_usd: number;
  cost_uncertain: boolean;
};

export type TurnView = {
  id: string;
  question: string;
  status: "running" | "completed" | "stopped" | "failed" | "paused";
  stop_reason: string | null;
  mode: string;
  model: string | null;
  answer: Answer | null;
  metrics: Metrics | null;
  proposal_ids: string[];
  carried: { turns: number; workbook_range: string | null; snapshot_id: string | null };
  started_at: string;
};

export type Progress = {
  kind:
    | "started"
    | "model"
    | "search"
    | "read"
    | "workbook_read"
    | "proposal"
    | "tool_error"
    | "final_synthesis"
    | "answer_rejected"
    | "finished";
  label: string;
  detail: Record<string, unknown>;
  t: number;
  cost_usd: number | null;
};

export type DocumentInfo = {
  id: string;
  title: string;
  published: string;
  url: string;
  has_original: boolean;
};

export type Corpus = {
  id: string;
  label: string;
  description: string;
  cutoff: string;
  documents: DocumentInfo[];
  starters: string[];
  workbook_starters: string[];
  scripted: string[];
};

export type Config = {
  live_available: boolean;
  replay: boolean;
  model: string | null;
  spend: { total_usd: number; cap_usd: number; remaining_usd: number };
  limits: Record<string, number>;
  corpora: Corpus[];
};

export type WorkbookInfo = {
  snapshot_id: string;
  filename: string;
  sha256: string;
  sheets: { name: string; max_row: number; max_col: number }[];
  warnings: string[];
};

export type Cell = { address: string; display: string; value: string; formula: string | null };

export type Grid = { sheet: string; max_row: number; max_col: number; rows: (Cell | null)[][] };

export type Proposal = {
  id: string;
  turn_id: string;
  snapshot_id: string;
  sheet: string;
  cell: string;
  old_display: string;
  old_formula: string | null;
  new_content: number | string;
  rationale: string;
  citations: Citation[];
  mode: string | null;
  model: string | null;
  generated_by: string | null;
  turn_status: string | null;
  status: "pending" | "stale" | "exported" | "superseded";
};

export type ExportRecord = {
  id: string;
  filename: string;
  snapshot_id: string;
  proposal_ids: string[];
  changes: { cell: string; old: string; new: number | string; generated_by: string | null }[];
  created_at: string;
  download_url: string;
};

export type Session = {
  id: string;
  corpus: string;
  turns: TurnView[];
  workbook: WorkbookInfo | null;
  context: { sheet: string; range: string } | null;
  proposals: Proposal[];
  exports: ExportRecord[];
};

export type SourceLine = {
  line: number;
  text: string;
  location: { page?: number; section?: string } | null;
};

export type SourceWindow = {
  id: string;
  title: string;
  url: string;
  published: string;
  total_lines: number;
  locator_note: string;
  has_original: boolean;
  original_type: string | null;
  lines: SourceLine[];
};

export type Selection =
  | { kind: "source"; citation: Citation }
  | { kind: "cell"; citation: Citation };

export type Tab = "evidence" | "activity" | "workbook" | "changes";
