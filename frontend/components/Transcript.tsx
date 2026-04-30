import React, { useMemo } from 'react';
import { Box, Text, useStdout } from 'ink';
import { useAppState } from '../hooks/useAppState.js';
import { COLOR } from '../rendering.js';
import { renderMessageLines } from '../messageLines.js';
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
  const renderedRows = items.flatMap((message, messageIndex) => {
    const rows = renderMessageLines(
      message,
      width,
      message.kind === 'tool' && message.id === selectedToolId,
    ).map((line, lineIndex) => ({
      key: `${message.id}-${lineIndex}`,
      line,
      messageId: message.id,
    }));
    if (messageIndex < items.length - 1) {
      rows.push({ key: `${message.id}-spacer`, line: '', messageId: message.id });
    }
    return rows;
  });
  const maxOffset = Math.max(0, renderedRows.length - visibleCount);
  const clampedOffset = Math.max(0, Math.min(maxOffset, transcriptScroll));
  const selectedRowIndex = selectedToolId
    ? renderedRows.findIndex((row) => row.messageId === selectedToolId)
    : -1;

  let start = Math.max(0, renderedRows.length - visibleCount - clampedOffset);
  if (selectedRowIndex >= 0) {
    const end = start + visibleCount;
    if (selectedRowIndex < start) {
      start = selectedRowIndex;
    } else if (selectedRowIndex >= end) {
      start = Math.max(0, selectedRowIndex - visibleCount + 1);
    }
  }
  const visible = renderedRows.slice(start, start + visibleCount);

  return (
    <Box flexDirection="column" paddingX={1} flexGrow={1}>
      {clampedOffset > 0 && (
        <Ansi>{`${COLOR.secondary}Showing older messages. Use PageUp/PageDown to scroll the in-app history.${COLOR.reset}`}</Ansi>
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
          visible.map((row) => (row.line ? <Ansi key={row.key}>{row.line}</Ansi> : <Text key={row.key}> </Text>))
        )}
      </Box>
    </Box>
  );
}
