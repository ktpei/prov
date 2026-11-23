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
    setReady(true); setMessage('Excel connected');
  }).catch(error => setMessage(error.message)); }, []);
  async function run(action: () => Promise<void>) {
    setWorking(true);
    try { await action(); } catch (error) { setMessage((error as Error).message); }
    finally { setWorking(false); }
  }
  const disabled = !ready || busy || working;
  return <section aria-label="Excel connection" className="border-b border-rule bg-surface p-3 text-sm">
    <p role="status">{message}</p>
    <div className="mt-2 flex flex-wrap gap-2">
      <button className="rounded border border-rule px-3 py-2 disabled:opacity-40" disabled={disabled}
        onClick={() => void run(async () => { onSelection(await readSelection()); setMessage('Selection attached. Its values and formulas will be sent with your next question.'); })}>Attach selected cells</button>
      {selection && <button onClick={() => onSelection('')} disabled={busy}>Remove selection</button>}
      <button className="rounded bg-ledger px-3 py-2 text-white disabled:opacity-40" disabled={disabled || !answer?.answerable || !answer.claims.length}
        onClick={() => void run(async () => { await insertAnswer(answer!); setMessage('Cited results inserted into a new worksheet.'); })}>Insert cited results</button>
    </div>
  </section>;
}
