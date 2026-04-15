import React, { useMemo } from 'react';
import { Box, Text, useStdout } from 'ink';
import { useAppState } from '../hooks/useAppState.js';
import { COLOR } from '../rendering.js';
import Message from './Message.js';
import Ansi from './Ansi.js';

export default function Transcript() {
  const { stdout } = useStdout();
  const { messages, selectedToolId, streaming, transcriptScroll, generating } = useAppState();

  const items = useMemo(() => {
    const base = [...messages];
    if (streaming) {
      base.push({
        id: '__streaming__',
        kind: 'message' as const,
        role: 'assistant' as const,
        content: streaming,
        timestamp: Date.now(),
      });
    }
    return base;
  }, [messages, streaming]);

  const width = Math.max(24, (stdout.columns || 80) - 2);
  const visibleCount = Math.max(4, (stdout.rows || 24) - 12);
  const emptyStateTopSpacing = Math.max(2, Math.min(3, Math.floor((stdout.rows || 24) * 0.12)));
  const maxOffset = Math.max(0, items.length - visibleCount);
  const clampedOffset = Math.max(0, Math.min(maxOffset, transcriptScroll));
  const selectedIndex = selectedToolId
    ? items.findIndex((message) => message.kind === 'tool' && message.id === selectedToolId)
    : -1;

  let start = Math.max(0, items.length - visibleCount - clampedOffset);
  if (selectedIndex >= 0) {
    const end = start + visibleCount;
    if (selectedIndex < start) {
      start = selectedIndex;
    } else if (selectedIndex >= end) {
      start = Math.max(0, selectedIndex - visibleCount + 1);
    }
  }

  const visible = items.slice(start, start + visibleCount);

  return (
    <Box flexDirection="column" paddingX={1} flexGrow={1}>
      {clampedOffset > 0 && (
        <Ansi>{`${COLOR.secondary}Showing older messages. PageDown returns to the latest output.${COLOR.reset}`}</Ansi>
      )}
      <Box flexDirection="column" flexGrow={1} justifyContent="flex-end">
        {visible.length === 0 && !generating ? (
          <Box flexDirection="column">
            {Array.from({ length: emptyStateTopSpacing }).map((_, index) => (
              <Text key={`empty-space-${index}`}> </Text>
            ))}
            <Ansi>{`${COLOR.secondary}  输入 / 打开命令列表，或使用 /help 查看全部命令。${COLOR.reset}`}</Ansi>
            <Text> </Text>
          </Box>
        ) : (
          visible.map((message) => (
            <Message
              key={message.id}
              message={message}
              width={width}
              selected={message.kind === 'tool' && message.id === selectedToolId}
            />
          ))
        )}
      </Box>
    </Box>
  );
}
