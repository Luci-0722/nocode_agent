import React, { useMemo } from 'react';
import { Box, Text, useStdout } from 'ink';
import { useAppState } from '../hooks/useAppState.js';
import Message from './Message.js';
import Ansi from './Ansi.js';

export default function Transcript() {
  const { stdout } = useStdout();
  const { messages, selectedToolId, streaming, transcriptScroll } = useAppState();

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

  const visibleCount = Math.max(4, (stdout.rows || 24) - 10);
  const maxOffset = Math.max(0, items.length - visibleCount);
  const clampedOffset = Math.max(0, Math.min(maxOffset, transcriptScroll));
  const start = Math.max(0, items.length - visibleCount - clampedOffset);
  const visible = items.slice(start, start + visibleCount);

  return (
    <Box flexDirection="column" paddingX={1}>
      {clampedOffset > 0 && (
        <Text dimColor>Showing older messages. PageDown returns to the latest output.</Text>
      )}
      {visible.length === 0 && (
        <Text dimColor>No messages yet.</Text>
      )}
      {visible.map((message) => (
        <Message
          key={message.id}
          message={message}
          selected={message.kind === 'tool' && message.id === selectedToolId}
        />
      ))}
      {streaming && visible[visible.length - 1]?.id !== '__streaming__' && (
        <Box flexDirection="column">
          <Text color="cyan" bold>
            Assistant
          </Text>
          <Ansi>{streaming}</Ansi>
        </Box>
      )}
    </Box>
  );
}
