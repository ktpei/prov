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

// Keep the host worksheet identities alongside the server snapshot; never apply
// an uploaded-file proposal to an unrelated open workbook.
export type ExcelBinding = { snapshotId: string; sheetIds: Record<string, string> };

export async function captureWorkbook(): Promise<{ file: File; sheetIds: Record<string, string> }> {
  await connectExcel();
  if (!Office.context.requirements.isSetSupported('CompressedFile', '1.1')) {
    throw new Error('Workbook tools require desktop Excel on Mac or Windows. This Excel host cannot share a workbook snapshot.');
  }
  const sheetIds = await Excel.run(async context => {
    const sheets = context.workbook.worksheets;
    sheets.load('items/name,items/id');
    await context.sync();
    return Object.fromEntries(sheets.items.map(sheet => [sheet.name, sheet.id]));
  });
  const file = await new Promise<Office.File>((resolve, reject) => {
    Office.context.document.getFileAsync(Office.FileType.Compressed, { sliceSize: 65536 }, result => {
      if (result.status === Office.AsyncResultStatus.Succeeded) resolve(result.value);
      else reject(new Error(result.error.message));
    });
  });
  try {
    if (file.size > 5 * 1024 * 1024) throw new Error('Workbook exceeds the 5 MB snapshot limit.');
    const parts: Uint8Array<ArrayBuffer>[] = [];
    for (let index = 0; index < file.sliceCount; index++) {
      const slice = await new Promise<Office.Slice>((resolve, reject) => {
        file.getSliceAsync(index, result => {
          if (result.status === Office.AsyncResultStatus.Succeeded) resolve(result.value);
          else reject(new Error(result.error.message));
        });
      });
      parts.push(new Uint8Array(slice.data as number[]));
    }
    return { file: new File(parts, 'Excel-workbook.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }), sheetIds };
  } finally {
    await new Promise<void>((resolve, reject) => file.closeAsync(result => {
      if (result.status === Office.AsyncResultStatus.Succeeded) resolve();
      else reject(new Error(result.error.message));
    }));
  }
}

export function selectionLocation(selection: string): { sheet: string; range: string } {
  const { address } = JSON.parse(selection) as { address: string };
  const separator = address.lastIndexOf('!');
  if (separator < 1) throw new Error('Select a range on one worksheet.');
  let sheet = address.slice(0, separator);
  if (sheet.startsWith("'") && sheet.endsWith("'")) sheet = sheet.slice(1, -1).replace(/''/g, "'");
  return { sheet, range: address.slice(separator + 1) };
}

export type ExcelEdit = {
  id: string; sheet: string; cell: string;
  old_content: string | number | boolean | null;
  new_content: string | number;
};

export async function applyExcelEdits(edits: ExcelEdit[], binding: ExcelBinding) {
  await connectExcel();
  if (!Office.context.requirements.isSetSupported('ExcelApi', '1.13')) {
    throw new Error('Applying changes requires ExcelApi 1.13. Update desktop Excel.');
  }
  if (!edits.length || edits.length > 10) throw new Error('Approve between 1 and 10 changes.');
  await Excel.run(async context => {
    const targets = edits.map(edit => {
      const sheet = context.workbook.worksheets.getItem(edit.sheet);
      sheet.load('id,visibility');
      sheet.protection.load('protected');
      const range = sheet.getRange(edit.cell);
      range.load('values,formulas,valueTypes,rowCount,columnCount,rowHidden,columnHidden');
      const merged = range.getMergedAreasOrNullObject();
      const spill = range.getSpillParentOrNullObject();
      const tables = range.getTables(false);
      tables.load('items/name');
      return { edit, sheet, range, merged, spill, tables };
    });
    await context.sync();
    for (const { edit, sheet, range, merged, spill, tables } of targets) {
      const current = range.values[0][0];
      const formula = range.formulas[0][0];
      if (sheet.id !== binding.sheetIds[edit.sheet]) throw new Error('The worksheet changed. Ask again on the current workbook.');
      if (range.rowCount !== 1 || range.columnCount !== 1 ||
          sheet.visibility !== Excel.SheetVisibility.visible || sheet.protection.protected ||
          range.rowHidden || range.columnHidden || range.valueTypes[0][0] === Excel.RangeValueType.error ||
          !merged.isNullObject || !spill.isNullObject || tables.items.length ||
          (typeof formula === 'string' && formula.startsWith('='))) {
        throw new Error(`Cannot edit ${edit.sheet}!${edit.cell}: only ordinary, visible, unprotected input cells are supported.`);
      }
      if (current !== (edit.old_content ?? '')) {
        throw new Error(`${edit.sheet}!${edit.cell} changed since the proposal. Ask again before applying.`);
      }
    }
    // Validate every target before any write. Office batches are not transactions:
    // report uncertain failures explicitly and never retry a write automatically.
    try {
      for (const { edit, range } of targets) range.values = [[literal(edit.new_content)]];
      await context.sync();
      context.workbook.application.calculate(Excel.CalculationType.full);
      for (const { range } of targets) range.load('values,formulas,valueTypes');
      await context.sync();
      for (const { edit, range } of targets) {
        if (range.values[0][0] !== edit.new_content || range.valueTypes[0][0] === Excel.RangeValueType.error ||
            (typeof range.formulas[0][0] === 'string' && range.formulas[0][0].startsWith('='))) {
          throw new Error(`Readback did not match ${edit.sheet}!${edit.cell}`);
        }
      }
    } catch (error) {
      throw new Error(`Excel may have applied some changes. Inspect the cells before asking again; do not retry blindly. ${(error as Error).message}`);
    }
  });
}
