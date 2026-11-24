import type { Answer } from './types';

export const inExcelPane = new URLSearchParams(location.search).has('excel');

export async function connectExcel() {
  if (typeof Office === 'undefined') throw new Error('Office.js did not load. Reopen the add-in in Excel.');
  const info = await Office.onReady();
  if (info.host !== Office.HostType.Excel) throw new Error('Open this add-in inside Excel.');
  if (!Office.context.requirements.isSetSupported('ExcelApi', '1.1')) throw new Error('This Excel version is unsupported.');
}

export async function readSelection(): Promise<string> {
  await connectExcel();
  return Excel.run(async context => {
    const range = context.workbook.getSelectedRange();
    range.load('address,rowCount,columnCount');
    await context.sync();
    if (range.rowCount * range.columnCount > 200) throw new Error('Select at most 200 cells.');
    range.load('values,formulas');
    await context.sync();
    const result = JSON.stringify({ address: range.address, values: range.values, formulas: range.formulas });
    if (result.length > 2500) throw new Error('The selection is too large. Select fewer cells.');
    return result;
  });
}

// Excel treats leading formula markers as executable input, even in values.
export const literal = (value: string | number): string | number =>
  typeof value === 'string' && /^[=+@-]/.test(value) ? `'${value}` : value;

export async function insertAnswer(answer: Answer) {
  await connectExcel();
  await Excel.run(async context => {
    const sheet = context.workbook.worksheets.add();
    const rows: (string | number)[][] = [
      ['Claim', 'Value', 'Unit', 'Period', 'Evidence'],
      ...answer.claims.map(c => [c.key, c.value, c.unit, c.period,
        c.citations.map(ref => `${ref.source_id} ${ref.locator}: ${ref.quote}`).join('\n')]),
    ];
    sheet.getRangeByIndexes(0, 0, rows.length, 5).values = rows.map(row => row.map(literal));
    sheet.getRange('A1:E1').format.font.bold = true;
    sheet.getRange('A:E').format.columnWidth = 140;
    sheet.getRangeByIndexes(0, 0, rows.length, 5).format.wrapText = true;
    sheet.activate();
    await context.sync();
  });
}
