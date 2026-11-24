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
  const attached = selection ? JSON.parse(selection) as {
    address: string; values: (string | number | boolean)[][];
  } : null;
  const cellCount = attached?.values.reduce((count, row) => count + row.length, 0) ?? 0;
  return <section aria-label="Excel connection" className="excel-tools">
    {message && <p role="status" className="excel-feedback">{message}</p>}
    {attached ? <div className="selection-attachment">
      <div className="selection-heading">
        <span className="selection-address">{attached.address}</span>
        <button type="button" onClick={() => { onSelection(''); setMessage(''); }} disabled={busy || working}
          aria-label="Remove selection" title="Remove attached cells">×</button>
      </div>
      <p>{cellCount} {cellCount === 1 ? 'cell' : 'cells'} attached · snapshot</p>
      <div className="selection-options">
        <details>
          <summary>Preview values</summary>
          <div className="selection-preview" tabIndex={0} aria-label="Attached cell values">
            <table><tbody>{attached.values.map((row, rowIndex) => <tr key={rowIndex}>
              {row.map((value, columnIndex) => <td key={columnIndex}>{String(value)}</td>)}
            </tr>)}</tbody></table>
          </div>
        </details>
        <button type="button" disabled={disabled} onClick={() => void run(async () => {
          onSelection(await readSelection()); setMessage('');
        })}>{working ? 'Reading…' : 'Update from selection'}</button>
      </div>
      <p className="selection-note">Values and formulas go with your next question. Update after editing cells.</p>
    </div> : <p className="selection-hint">Select a range in Excel, then attach it to your question.</p>}
    <div className="excel-actions">
      {!attached && <button type="button" className="rounded border border-rule px-3 py-2 disabled:opacity-40" disabled={disabled}
        onClick={() => void run(async () => { onSelection(await readSelection()); setMessage(''); })}>{working ? 'Reading…' : 'Attach selected cells'}</button>}
      {answer?.answerable && answer.claims.length > 0 && <button type="button" className="rounded bg-ledger px-3 py-2 text-white disabled:opacity-40" disabled={disabled || !answer?.answerable || !answer.claims.length}
        onClick={() => void run(async () => { await insertAnswer(answer!); setMessage('Cited results inserted into a new worksheet.'); })}>Insert cited results</button>}
    </div>
  </section>;
}
