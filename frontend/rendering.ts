import os from 'node:os';
import process from 'node:process';

export const COLOR = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  italic: '\x1b[3m',
  underline: '\x1b[4m',
  strikethrough: '\x1b[9m',
  soft: '\x1b[38;2;186;198;207m',
  accent: '\x1b[38;2;95;215;175m',
  assistant: '\x1b[38;2;200;210;220m',
  secondary: '\x1b[38;2;138;153;166m',
  warning: '\x1b[38;2;244;211;94m',
  danger: '\x1b[38;2;255;107;107m',
  user: '\x1b[38;2;126;217;87m',
  tool: '\x1b[38;2;255;167;38m',
  toolBg: '\x1b[48;2;45;35;25m',
  selectedBg: '\x1b[48;2;45;65;85m',
  selectedBorder: '\x1b[38;2;95;215;175m',
  selectedText: '\x1b[38;2;230;238;242m',
  selectedSubtle: '\x1b[38;2;168;191;201m',
  md: {
    heading: '\x1b[38;2;95;215;175m\x1b[1m',
    headingBold: '\x1b[38;2;95;215;175m\x1b[1m',
    code: '\x1b[38;2;186;198;207m',
    codeBg: '',
    strong: '\x1b[1m',
    link: '\x1b[38;2;104;179;215m\x1b[4m',
    blockquote: '\x1b[38;2;139;153;166m',
    hr: '\x1b[38;2;80;80;80m',
    listBullet: '\x1b[38;2;95;215;175m',
    tableBorder: '\x1b[38;2;80;90;100m',
    tableHeader: '\x1b[38;2;186;198;207m\x1b[1m',
  },
} as const;

export const TUI_GLYPH_PROFILE =
  String(process.env.NOCODE_TUI_GLYPHS || '').trim().toLowerCase() === 'rich'
    ? 'rich'
    : 'portable';

const PORTABLE_GLYPHS = {
  assistantLeader: '* ',
  userLeader: '> ',
  toolDetailLeader: '  -> ',
  subagentLeader: '    -> ',
  spinnerFrames: ['|', '/', '-', '\\'],
  orbitFrames: ['|', '/', '-', '\\'],
  pulseFrames: ['.', 'o', '.', 'o'],
  signalHead: '*',
  signalTail: 'o',
  signalDot: '.',
  box: { topLeft: '+', topRight: '+', bottomLeft: '+', bottomRight: '+', horizontal: '-', vertical: '|' },
} as const;

const RICH_GLYPHS = {
  assistantLeader: '⏺ ',
  userLeader: '❯ ',
  toolDetailLeader: '  ⎿ ',
  subagentLeader: '    ↳ ',
  spinnerFrames: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
  orbitFrames: ['◐', '◓', '◑', '◒'],
  pulseFrames: ['✦', '✧', '·', '✧'],
  signalHead: '◆',
  signalTail: '◇',
  signalDot: '·',
  box: { topLeft: '┌', topRight: '┐', bottomLeft: '└', bottomRight: '┘', horizontal: '─', vertical: '│' },
} as const;

export const UI_GLYPHS = TUI_GLYPH_PROFILE === 'rich' ? RICH_GLYPHS : PORTABLE_GLYPHS;
export const GENERATING_SPINNER_FRAMES = UI_GLYPHS.spinnerFrames;

export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (minutes < 60) {
    return secs > 0 ? `${minutes}m${secs}s` : `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h${mins}m` : `${hours}h`;
}

export function stripAnsi(text: string): string {
  return text
    .replace(/\x1b\[[0-9;]*[mK]/g, '')
    .replace(/[0-9]+;[0-9;]*m/g, '')
    .replace(/\x1b/g, '');
}

export function charWidth(char: string): number {
  const codePoint = char.codePointAt(0);
  if (codePoint === undefined) {
    return 0;
  }
  if (
    codePoint === 0 ||
    codePoint < 32 ||
    (codePoint >= 0x7f && codePoint < 0xa0) ||
    (codePoint >= 0x300 && codePoint <= 0x36f) ||
    (codePoint >= 0x200b && codePoint <= 0x200f) ||
    (codePoint >= 0xfe00 && codePoint <= 0xfe0f)
  ) {
    return 0;
  }
  if (
    codePoint >= 0x1100 &&
    (codePoint <= 0x115f ||
      codePoint === 0x2329 ||
      codePoint === 0x232a ||
      (codePoint >= 0x2e80 && codePoint <= 0xa4cf && codePoint !== 0x303f) ||
      (codePoint >= 0xac00 && codePoint <= 0xd7a3) ||
      (codePoint >= 0xf900 && codePoint <= 0xfaff) ||
      (codePoint >= 0xfe10 && codePoint <= 0xfe19) ||
      (codePoint >= 0xfe30 && codePoint <= 0xfe6f) ||
      (codePoint >= 0xff00 && codePoint <= 0xff60) ||
      (codePoint >= 0xffe0 && codePoint <= 0xffe6) ||
      (codePoint >= 0x1f300 && codePoint <= 0x1faf6) ||
      (codePoint >= 0x20000 && codePoint <= 0x3fffd))
  ) {
    return 2;
  }
  return 1;
}

export function visibleLength(text: string): number {
  return Array.from(stripAnsi(text)).reduce((sum, char) => sum + charWidth(char), 0);
}

export function sliceByWidth(text: string, width: number): string {
  if (width <= 0) {
    return '';
  }
  let result = '';
  let consumed = 0;
  for (const char of Array.from(text)) {
    const widthOfChar = charWidth(char);
    if (consumed + widthOfChar > width) {
      break;
    }
    result += char;
    consumed += widthOfChar;
  }
  return result;
}

export function truncate(text: string, width: number): string {
  if (visibleLength(text) <= width) {
    return text;
  }
  if (width <= 0) {
    return '';
  }
  if (width === 1) {
    return '…';
  }
  return `${sliceByWidth(text, width - 1)}…`;
}

export function wrap(text: string, width: number): string[] {
  return text.split('\n').flatMap((line) => {
    if (!line) {
      return [''];
    }
    const parts: string[] = [];
    let remaining = line;
    while (visibleLength(remaining) > width) {
      const chunk = sliceByWidth(remaining, width);
      parts.push(chunk);
      remaining = remaining.slice(chunk.length);
    }
    parts.push(remaining);
    return parts;
  });
}

export function truncateAnsiAware(text: string, width: number): string {
  if (visibleLength(text) <= width) {
    return text;
  }
  if (width <= 0) {
    return '';
  }

  let result = '';
  let visible = 0;
  const ansiPattern = /\x1b\[[0-9;]*m/g;
  let index = 0;

  while (index < text.length && visible < Math.max(0, width - 1)) {
    ansiPattern.lastIndex = index;
    const ansiMatch = ansiPattern.exec(text);
    if (ansiMatch && ansiMatch.index === index) {
      result += ansiMatch[0];
      index += ansiMatch[0].length;
      continue;
    }

    const char = Array.from(text.slice(index))[0];
    if (!char) {
      break;
    }
    const widthOfChar = charWidth(char);
    if (visible + widthOfChar > Math.max(0, width - 1)) {
      break;
    }
    result += char;
    visible += widthOfChar;
    index += char.length;
  }

  return `${result}…${COLOR.reset}`;
}

export function sliceByWidthAnsi(text: string, width: number): [string, string] {
  let result = '';
  let lastIndex = 0;
  let visiblePos = 0;
  let activeStyles = '';

  const ansiRegex = /\x1b\[[0-9;]*m/g;
  const sequences: Array<{ index: number; length: number; code: string }> = [];
  let match: RegExpExecArray | null;
  ansiRegex.lastIndex = 0;
  while ((match = ansiRegex.exec(text)) !== null) {
    sequences.push({ index: match.index, length: match[0].length, code: match[0] });
  }

  let seqIndex = 0;
  for (const char of Array.from(text)) {
    const charPos = text.indexOf(char, lastIndex);

    while (seqIndex < sequences.length && sequences[seqIndex].index < charPos + char.length) {
      const sequence = sequences[seqIndex];
      if (sequence.index >= lastIndex && sequence.index <= charPos) {
        activeStyles += sequence.code;
        seqIndex += 1;
      } else {
        break;
      }
    }

    const widthOfChar = charWidth(char);
    if (visiblePos + widthOfChar > width) {
      return [result + COLOR.reset, activeStyles + text.slice(charPos)];
    }

    result += char;
    visiblePos += widthOfChar;
    lastIndex = charPos + char.length;
  }

  return [result, ''];
}

export function wrapAnsiAware(text: string, width: number): string[] {
  return text.split('\n').flatMap((line) => {
    if (!line || visibleLength(line) <= width) {
      return [line];
    }

    const parts: string[] = [];
    let remaining = line;
    while (visibleLength(remaining) > width) {
      const [chunk, rest] = sliceByWidthAnsi(remaining, width);
      parts.push(chunk);
      remaining = rest;
    }
    parts.push(remaining);
    return parts;
  });
}

export function padRight(text: string, width: number): string {
  const visible = visibleLength(text);
  if (visible >= width) {
    return text;
  }
  return text + ' '.repeat(width - visible);
}

export function tildePath(target: string): string {
  const home = os.homedir();
  if (!home || !target.startsWith(home)) {
    return target;
  }
  if (target === home) {
    return '~';
  }
  return `~${target.slice(home.length)}`;
}

export function renderInlineMarkdown(text: string): string {
  let result = text;

  result = result.replace(/`([^`]+)`/g, (_, code) => `\x00CODE_START\x00${code}\x00CODE_END\x00`);
  result = result.replace(/\*\*\*(.+?)\*\*\*/g, (_, inner) => `\x00BI_START\x00${inner}\x00BI_END\x00`);
  result = result.replace(/\*\*(.+?)\*\*/g, (_, inner) => `\x00B_START\x00${inner}\x00B_END\x00`);
  result = result.replace(/(?<!\*)\*([^*]+?)\*(?!\*)/g, (_, inner) => `\x00I_START\x00${inner}\x00I_END\x00`);
  result = result.replace(/~~(.+?)~~/g, (_, inner) => `\x00S_START\x00${inner}\x00S_END\x00`);
  result = result.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    (_, linkText, url) => `\x00LINK_START\x00${linkText}\x00LINK_MID\x00${url}\x00LINK_END\x00`,
  );

  result = result
    .replace(/\x00CODE_START\x00/g, `${COLOR.md.codeBg}${COLOR.md.code}`)
    .replace(/\x00CODE_END\x00/g, COLOR.reset)
    .replace(/\x00BI_START\x00/g, `${COLOR.md.strong}${COLOR.italic}`)
    .replace(/\x00BI_END\x00/g, COLOR.reset)
    .replace(/\x00B_START\x00/g, COLOR.md.strong)
    .replace(/\x00B_END\x00/g, COLOR.reset)
    .replace(/\x00I_START\x00/g, COLOR.italic)
    .replace(/\x00I_END\x00/g, COLOR.reset)
    .replace(/\x00S_START\x00/g, COLOR.strikethrough)
    .replace(/\x00S_END\x00/g, COLOR.reset)
    .replace(/\x00LINK_START\x00/g, COLOR.md.link)
    .replace(/\x00LINK_MID\x00/g, `${COLOR.reset} `)
    .replace(/\x00LINK_END\x00/g, COLOR.reset);

  return `${COLOR.assistant}${result}${COLOR.reset}`;
}

export function renderMarkdownTable(tableRows: string[]): string[] {
  if (tableRows.length === 0) {
    return [];
  }

  const parsedRows: string[][] = [];
  for (const row of tableRows) {
    if (/^\|[\s\-:|]+\|$/.test(row.trim())) {
      continue;
    }
    parsedRows.push(row.split('|').slice(1, -1).map((cell) => cell.trim()));
  }

  if (parsedRows.length === 0) {
    return [];
  }

  const colCount = Math.max(...parsedRows.map((row) => row.length));
  const colWidths: number[] = [];
  for (let column = 0; column < colCount; column += 1) {
    let maxWidth = 0;
    for (const row of parsedRows) {
      maxWidth = Math.max(maxWidth, visibleLength(row[column] || ''));
    }
    colWidths.push(maxWidth);
  }

  const lines: string[] = [];
  const border = COLOR.md.tableBorder;

  for (let rowIndex = 0; rowIndex < parsedRows.length; rowIndex += 1) {
    const row = parsedRows[rowIndex] || [];
    const styledCells = colWidths.map((width, column) => {
      const cell = row[column] || '';
      const isHeader = rowIndex === 0;
      const styled = isHeader
        ? `${COLOR.md.tableHeader}${cell}${COLOR.reset}`
        : `${COLOR.soft}${cell}${COLOR.reset}`;
      const padding = ' '.repeat(Math.max(0, width - visibleLength(cell)));
      return ` ${styled}${padding} `;
    });
    lines.push(`${border}│${COLOR.reset}${styledCells.join(`${border}│${COLOR.reset}`)}${border}│${COLOR.reset}`);

    if (rowIndex === 0) {
      const separator = colWidths.map((width) => `${border}${'─'.repeat(width + 2)}${COLOR.reset}`);
      lines.push(`${border}├${COLOR.reset}${separator.join(`${border}┼${COLOR.reset}`)}${border}┤${COLOR.reset}`);
    }
  }

  return lines;
}

export function renderMarkdownLines(content: string, width: number): string[] {
  const lines: string[] = [];
  const sourceLines = content.split('\n');
  let index = 0;

  while (index < sourceLines.length) {
    const raw = sourceLines[index] || '';

    const fenceMatch = raw.match(/^(\s*)```/);
    if (fenceMatch) {
      const fenceIndent = fenceMatch[1] || '';
      const codeLines: string[] = [];
      index += 1;
      while (index < sourceLines.length && !sourceLines[index]?.match(/^\s*```/)) {
        codeLines.push(sourceLines[index] || '');
        index += 1;
      }
      index += 1;
      if (codeLines.length === 0) {
        lines.push(`${COLOR.md.code}${fenceIndent}  ${COLOR.reset}`);
      } else {
        for (const codeLine of codeLines) {
          lines.push(`${COLOR.md.code}${fenceIndent}  ${codeLine}${COLOR.reset}`);
        }
      }
      continue;
    }

    if (raw.includes('|') && raw.trim().startsWith('|')) {
      const tableBlock: string[] = [];
      while (index < sourceLines.length && sourceLines[index]?.includes('|') && sourceLines[index]?.trim().startsWith('|')) {
        tableBlock.push(sourceLines[index] || '');
        index += 1;
      }
      lines.push(...renderMarkdownTable(tableBlock));
      continue;
    }

    const headingMatch = raw.match(/^(#{1,6})\s+(.*)/);
    if (headingMatch) {
      const level = headingMatch[1]?.length || 1;
      const prefix = `▎${' '.repeat(Math.max(0, 4 - level))}`;
      lines.push('');
      lines.push(`${COLOR.md.headingBold}${prefix}${renderInlineMarkdown(headingMatch[2] || '')}${COLOR.reset}`);
      lines.push('');
      index += 1;
      continue;
    }

    if (/^(\s*[-*_]){3,}\s*$/.test(raw)) {
      lines.push(`${COLOR.md.hr}${'─'.repeat(width)}${COLOR.reset}`);
      index += 1;
      continue;
    }

    if (raw.startsWith('>')) {
      while (index < sourceLines.length && sourceLines[index]?.startsWith('>')) {
        const quote = (sourceLines[index] || '').replace(/^>\s?/, '');
        const wrapped = wrapAnsiAware(renderInlineMarkdown(quote), Math.max(4, width - 2));
        for (const line of wrapped) {
          lines.push(`${COLOR.md.blockquote}▎ ${line}${COLOR.reset}`);
        }
        index += 1;
      }
      continue;
    }

    if (/^\s*[-*+]\s/.test(raw)) {
      while (index < sourceLines.length && /^\s*[-*+]\s/.test(sourceLines[index] || '')) {
        const itemText = (sourceLines[index] || '').replace(/^\s*[-*+]\s/, '');
        const wrapped = wrapAnsiAware(renderInlineMarkdown(itemText), Math.max(4, width - 2));
        wrapped.forEach((line, itemIndex) => {
          lines.push(itemIndex === 0 ? `${COLOR.md.listBullet}• ${COLOR.reset}${line}` : `  ${line}`);
        });
        index += 1;
      }
      continue;
    }

    if (/^\s*\d+\.\s/.test(raw)) {
      let order = 1;
      while (index < sourceLines.length && /^\s*\d+\.\s/.test(sourceLines[index] || '')) {
        const itemText = (sourceLines[index] || '').replace(/^\s*\d+\.\s/, '');
        const wrapped = wrapAnsiAware(renderInlineMarkdown(itemText), Math.max(4, width - 4));
        wrapped.forEach((line, itemIndex) => {
          lines.push(itemIndex === 0 ? `${COLOR.md.listBullet}${String(order).padStart(2)}. ${COLOR.reset}${line}` : `    ${line}`);
        });
        order += 1;
        index += 1;
      }
      continue;
    }

    if (!raw.trim()) {
      lines.push('');
      index += 1;
      continue;
    }

    lines.push(...wrapAnsiAware(renderInlineMarkdown(raw), width));
    index += 1;
  }

  return lines;
}
