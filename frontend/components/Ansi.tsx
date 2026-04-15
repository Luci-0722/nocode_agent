import React from 'react';
import { Box, Text } from 'ink';

interface AnsiToken {
  text: string;
  color?: string;
  backgroundColor?: string;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  dimColor?: boolean;
}

const FG: Record<number, string> = {
  30: 'black',
  31: 'red',
  32: 'green',
  33: 'yellow',
  34: 'blue',
  35: 'magenta',
  36: 'cyan',
  37: 'white',
  90: 'gray',
  91: 'red',
  92: 'green',
  93: 'yellow',
  94: 'blue',
  95: 'magenta',
  96: 'cyan',
  97: 'white',
};

const BG: Record<number, string> = {
  40: 'black',
  41: 'red',
  42: 'green',
  43: 'yellow',
  44: 'blue',
  45: 'magenta',
  46: 'cyan',
  47: 'white',
  100: 'gray',
  101: 'red',
  102: 'green',
  103: 'yellow',
  104: 'blue',
  105: 'magenta',
  106: 'cyan',
  107: 'white',
};

function cloneStyle(token: AnsiToken): Omit<AnsiToken, 'text'> {
  return {
    color: token.color,
    backgroundColor: token.backgroundColor,
    bold: token.bold,
    italic: token.italic,
    underline: token.underline,
    dimColor: token.dimColor,
  };
}

function pushToken(tokens: AnsiToken[], current: AnsiToken) {
  if (!current.text) {
    return;
  }
  tokens.push({ ...current });
  current.text = '';
}

function parseAnsi(text: string): AnsiToken[] {
  const regex = /\x1b\[[0-9;]*m/g;
  const tokens: AnsiToken[] = [];
  let current: AnsiToken = { text: '' };
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      current.text += text.slice(lastIndex, match.index);
    }

    pushToken(tokens, current);
    const next: AnsiToken = { text: '', ...cloneStyle(current) };
    const params = match[0]
      .slice(2, -1)
      .split(';')
      .filter(Boolean)
      .map(Number);

    if (params.length === 0 || params.includes(0)) {
      current = { text: '' };
    } else {
      current = next;
      for (const param of params) {
        if (param === 1) current.bold = true;
        else if (param === 2) current.dimColor = true;
        else if (param === 3) current.italic = true;
        else if (param === 4) current.underline = true;
        else if (FG[param]) current.color = FG[param];
        else if (BG[param]) current.backgroundColor = BG[param];
      }
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    current.text += text.slice(lastIndex);
  }
  pushToken(tokens, current);
  return tokens;
}

export function stripAnsi(text: string): string {
  return text
    .replace(/\x1b\[[0-9;]*[mK]/g, '')
    .replace(/[0-9]+;[0-9;]*m/g, '')
    .replace(/\x1b/g, '');
}

interface Props {
  children: string;
}

export default function Ansi({ children }: Props) {
  const tokens = parseAnsi(children);
  if (tokens.length === 0) {
    return <Text>{stripAnsi(children)}</Text>;
  }

  return (
    <Box flexDirection="column">
      <Text>
        {tokens.map((token, index) => (
          <Text
            key={index}
            color={token.color}
            backgroundColor={token.backgroundColor}
            bold={token.bold}
            italic={token.italic}
            underline={token.underline}
            dimColor={token.dimColor}
          >
            {token.text}
          </Text>
        ))}
      </Text>
    </Box>
  );
}
