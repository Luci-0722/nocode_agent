import React from 'react';
import { Box, Text } from 'ink';

interface AnsiToken {
  text: string;
  color?: string;
  bgColor?: string;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  dim?: boolean;
}

// ANSI 颜色映射
const ANSI_COLORS: Record<number, string> = {
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

const ANSI_BG_COLORS: Record<number, string> = {
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

/**
 * 解析 ANSI 序列并转换为 token 数组
 */
function parseAnsi(text: string): AnsiToken[] {
  const tokens: AnsiToken[] = [];
  let current: AnsiToken = { text: '' };
  
  // 匹配 ANSI 序列：ESC [ ... m 或 ESC [ ... K
  const ansiRegex = /\x1b\[[0-9;]*[mK]/g;
  let lastIndex = 0;
  let match;
  
  while ((match = ansiRegex.exec(text)) !== null) {
    // 添加前面的文本
    if (match.index > lastIndex) {
      current.text += text.slice(lastIndex, match.index);
    }
    
    // 解析 ANSI 序列
    const sequence = match[0];
    const params = sequence.slice(2, -1).split(';').map(Number);
    
    for (const param of params) {
      if (param === 0) {
        // 重置
        current = { text: '' };
      } else if (param === 1) {
        current.bold = true;
      } else if (param === 2) {
        current.dim = true;
      } else if (param === 3) {
        current.italic = true;
      } else if (param === 4) {
        current.underline = true;
      } else if (ANSI_COLORS[param]) {
        current.color = ANSI_COLORS[param];
      } else if (ANSI_BG_COLORS[param]) {
        current.bgColor = ANSI_BG_COLORS[param];
      }
    }
    
    lastIndex = match.index + sequence.length;
  }
  
  // 添加剩余文本
  if (lastIndex < text.length) {
    current.text += text.slice(lastIndex);
  }
  
  // 只返回有文本的 token
  if (current.text) {
    tokens.push(current);
  }
  
  return tokens;
}

/**
 * 清理 ANSI 序列（用于简单显示）
 */
export function stripAnsi(text: string): string {
  // 匹配 ANSI 序列：ESC [ ... m 或 ESC [ ... K
  // 也匹配可能分片的序列（防御性处理）
  return text
    .replace(/\x1b\[[0-9;]*[mK]/g, '')
    .replace(/[0-9]+;[0-9;]*m/g, '') // 防御性处理分片残留
    .replace(/\x1b/g, '');
}

interface Props {
  children: string;
  maxLength?: number;
}

/**
 * ANSI 渲染组件
 */
export default function Ansi({ children, maxLength = 10000 }: Props) {
  const text = children.length > maxLength ? children.slice(0, maxLength) + '...' : children;
  
  // 如果文本太短或没有 ANSI 序列，直接显示
  if (text.length < 100 && !text.includes('\x1b')) {
    return <Text>{text}</Text>;
  }
  
  // 解析 ANSI 序列
  const tokens = parseAnsi(text);
  
  if (tokens.length === 0) {
    return <Text>{stripAnsi(text)}</Text>;
  }
  
  return (
    <Box flexDirection="column">
      {tokens.map((token, index) => (
        <Text
          key={index}
          color={token.color}
          backgroundColor={token.bgColor}
          bold={token.bold}
          italic={token.italic}
          dimColor={token.dim}
        >
          {token.text}
        </Text>
      ))}
    </Box>
  );
}