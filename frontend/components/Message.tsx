import React from 'react';
import { Box, Text } from 'ink';
import type { Message as MessageType } from '../hooks/useAppState.js';
import { renderMessageLines } from '../messageLines.js';
import Ansi from './Ansi.js';

interface Props {
  message: MessageType;
  width: number;
  selected?: boolean;
}

function renderAnsiLine(line: string, key: string) {
  if (!line) {
    return <Text key={key}> </Text>;
  }
  return <Ansi key={key}>{line}</Ansi>;
}

export default function Message({ message, width, selected = false }: Props) {
  const lines = renderMessageLines(message, width, selected);
  return <Box flexDirection="column" marginBottom={1}>{lines.map((line, index) => renderAnsiLine(line, `${message.id}-${index}`))}</Box>;
}
