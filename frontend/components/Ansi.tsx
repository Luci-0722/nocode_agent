import React from 'react';
import { Box, Text } from 'ink';
import { stripAnsi } from '../rendering.js';

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
      .filter((value) => value.length > 0)
      .map(Number);

    if (params.length === 0 || params.includes(0)) {
      current = { text: '' };
    } else {
      current = next;
      for (let index = 0; index < params.length; index += 1) {
        const param = params[index];
        if (param === undefined) {
          continue;
        }
        if (param === 1) current.bold = true;
        else if (param === 2) current.dimColor = true;
        else if (param === 3) current.italic = true;
        else if (param === 4) current.underline = true;
        else if (param === 22) current.bold = undefined;
        else if (param === 23) current.italic = undefined;
        else if (param === 24) current.underline = undefined;
        else if (param === 39) current.color = undefined;
        else if (param === 49) current.backgroundColor = undefined;
        else if (FG[param]) current.color = FG[param];
        else if (BG[param]) current.backgroundColor = BG[param];
        else if (param === 38 && params[index + 1] === 2) {
          const red = params[index + 2] ?? 0;
          const green = params[index + 3] ?? 0;
          const blue = params[index + 4] ?? 0;
          current.color = `#${red.toString(16).padStart(2, '0')}${green.toString(16).padStart(2, '0')}${blue.toString(16).padStart(2, '0')}`;
          index += 4;
        } else if (param === 48 && params[index + 1] === 2) {
          const red = params[index + 2] ?? 0;
          const green = params[index + 3] ?? 0;
          const blue = params[index + 4] ?? 0;
          current.backgroundColor = `#${red.toString(16).padStart(2, '0')}${green.toString(16).padStart(2, '0')}${blue.toString(16).padStart(2, '0')}`;
          index += 4;
        }
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
