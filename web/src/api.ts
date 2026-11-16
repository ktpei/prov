import type {
  Config,
  ExportRecord,
  Grid,
  Progress,
  Session,
  SourceWindow,
  TurnView,
  WorkbookInfo,
} from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError(0, "Cannot reach the local server. Check that it is still running.");
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const getConfig = () => request<Config>("/api/config");
export const createSession = (corpus: string) =>
  request<Session>("/api/sessions", json("POST", { corpus }));
export const getSession = (id: string) => request<Session>(`/api/sessions/${id}`);
export const getSourceWindow = (corpus: string, id: string, start: number, end: number) =>
  request<SourceWindow>(
    `/api/sources/${corpus}/${encodeURIComponent(id)}?start=${start}&end=${end}`,
  );
export const originalUrl = (corpus: string, id: string) =>
  `/api/sources/${corpus}/${encodeURIComponent(id)}/original`;
export const startTurn = (sid: string, question: string, mode: "live" | "replay") =>
  request<{ turn_id: string }>(`/api/sessions/${sid}/turns`, json("POST", { question, mode }));
export const uploadWorkbook = (sid: string, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return request<WorkbookInfo>(`/api/sessions/${sid}/workbook`, { method: "POST", body: form });
};
export const getGrid = (sid: string, sheet: string) =>
  request<Grid>(`/api/sessions/${sid}/workbook/${encodeURIComponent(sheet)}`);
export const setContext = (sid: string, sheet: string, range: string) =>
  request<{ sheet: string; range: string; cells: number }>(
    `/api/sessions/${sid}/context`,
    json("PUT", { sheet, range }),
  );
export const clearContext = (sid: string) =>
  request(`/api/sessions/${sid}/context`, { method: "DELETE" });
export const createExport = (sid: string, snapshotId: string, ids: string[]) =>
  request<ExportRecord>(
    `/api/sessions/${sid}/exports`,
    json("POST", { snapshot_id: snapshotId, proposal_ids: ids }),
  );

/** Subscribe to a turn's progress. Returns an unsubscribe function. */
export function streamTurn(
  sid: string,
  tid: string,
  onProgress: (event: Progress, id: number) => void,
  onDone: (turn: TurnView) => void,
  onError: (message: string) => void,
): () => void {
  const source = new EventSource(`/api/sessions/${sid}/turns/${tid}/events`);
  let finished = false;
  source.addEventListener("progress", (event) => {
    const message = event as MessageEvent;
    onProgress(JSON.parse(message.data), Number(message.lastEventId));
  });
  source.addEventListener("done", (event) => {
    finished = true;
    source.close();
    onDone(JSON.parse((event as MessageEvent).data));
  });
  source.onerror = () => {
    if (finished) return;
    if (source.readyState === EventSource.CLOSED) {
      onError("Lost the progress stream. Refresh to see the final result.");
    }
  };
  return () => {
    finished = true;
    source.close();
  };
}
export const useDemoWorkbook = (sid: string) =>
  request<WorkbookInfo>(`/api/sessions/${sid}/workbook/demo`, { method: "POST" });
