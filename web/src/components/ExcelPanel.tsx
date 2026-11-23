import { useEffect, useState } from 'react';
import { connectExcel, insertAnswer, readSelection } from '../excel';
import type { Answer } from '../types';

export function ExcelPanel({ answer, busy, selection, onSelection }: {
  answer: Answer | null; busy: boolean; selection: string;
  onSelection: (value: string) => void;
}) {
  const [ready, setReady] = useState(false);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState('Connecting to Excel…');
  useEffect(() => { void connectExcel().then(() => {
    setReady(true); setMessage('');
  }).catch(error => setMessage(error.message)); }, []);
  async function run(action: () => Promise<void>) {
    setWorking(true);
    try { await action(); } catch (error) { setMessage((error as Error).message); }
    finally { setWorking(false); }
  }
  const disabled = !ready || busy || working;
  return <section aria-label="Excel connection" className="border-b border-rule bg-surface p-3 text-sm">
    {message && <p role="status">{message}</p>}
    {selection && <p>Selected values and formulas will be sent with your question.</p>}
    <div className="mt-2 flex flex-wrap gap-2">
      <button className="rounded border border-rule px-3 py-2 disabled:opacity-40" disabled={disabled}
        onClick={() => void run(async () => { onSelection(await readSelection()); setMessage(''); })}>Attach selected cells</button>
      {selection && <button onClick={() => { onSelection(''); setMessage(''); }} disabled={busy}>Remove selection</button>}
      {answer?.answerable && answer.claims.length > 0 && <button className="rounded bg-ledger px-3 py-2 text-white disabled:opacity-40" disabled={disabled || !answer?.answerable || !answer.claims.length}
        onClick={() => void run(async () => { await insertAnswer(answer!); setMessage('Cited results inserted into a new worksheet.'); })}>Insert cited results</button>}
    </div>
  </section>;
}
