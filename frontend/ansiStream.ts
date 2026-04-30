const CSI_FINAL_BYTE = /[@-~]/;

export function stripDanglingAnsiFragments(text: string): string {
  return text
    .replace(/\x1b\[[0-9;]*[A-Za-z]/g, '')
    .replace(/(?:^|[\s(])\[[0-9;]{2,}[A-Za-z]/g, (match) => {
      const prefix = match.startsWith('[') ? '' : match[0];
      const body = match.startsWith('[') ? match : match.slice(1);
      return /^\[[0-9;]+[A-Za-z]$/.test(body) ? prefix : match;
    })
    .replace(/\x1b/g, '');
}

export class AnsiTextStream {
  private pending = '';

  push(chunk: string): string {
    if (!chunk) {
      return '';
    }

    const input = this.pending + chunk;
    let output = '';
    let index = 0;

    while (index < input.length) {
      const char = input[index];
      if (char !== '\x1b') {
        output += char;
        index += 1;
        continue;
      }

      if (index === input.length - 1) {
        this.pending = input.slice(index);
        return stripDanglingAnsiFragments(output);
      }

      const next = input[index + 1];
      if (next !== '[') {
        index += 1;
        continue;
      }

      let cursor = index + 2;
      while (cursor < input.length) {
        const current = input[cursor];
        if (CSI_FINAL_BYTE.test(current)) {
          cursor += 1;
          break;
        }
        cursor += 1;
      }

      if (cursor > input.length - 1 && !CSI_FINAL_BYTE.test(input[input.length - 1] || '')) {
        this.pending = input.slice(index);
        return stripDanglingAnsiFragments(output);
      }

      index = cursor;
    }

    this.pending = '';
    return stripDanglingAnsiFragments(output);
  }

  reset(): void {
    this.pending = '';
  }
}

export function sanitizeAnsiText(text: string): string {
  const stream = new AnsiTextStream();
  const sanitized = stream.push(text);
  stream.reset();
  return sanitized;
}
