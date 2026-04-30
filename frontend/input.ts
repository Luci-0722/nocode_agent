const BRACKETED_PASTE_START = '\u001B[200~';
const BRACKETED_PASTE_END = '\u001B[201~';

interface KeyModifiers {
  ctrl?: boolean;
  meta?: boolean;
}

export function normalizePastedText(text: string): string {
  return text
    .replaceAll(BRACKETED_PASTE_START, '')
    .replaceAll(BRACKETED_PASTE_END, '')
    .replace(/\r\n?/g, '\n')
    .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, '');
}

export function isPrintableInput(input: string, key: KeyModifiers): boolean {
  return Boolean(input) && !key.ctrl && !key.meta && !/[\u0000-\u001f\u007f]/.test(input);
}
