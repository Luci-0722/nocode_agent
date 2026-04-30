import React, { useEffect, useMemo, useState } from 'react';
import { Box, Text, useStdout } from 'ink';
import { useAppState } from '../hooks/useAppState.js';
import { COLOR, padRight, truncate } from '../rendering.js';
import { renderMessageLines } from '../messageLines.js';
import Ansi from './Ansi.js';

const ORBIT_FRAMES = ['◐', '◓', '◑', '◒'];
const GLYPH_FRAMES = ['✦', '✧', '·', '✧'];

function buildSignalBar(width: number, tick: number, color: string): string {
  const length = Math.max(14, Math.min(width, 28));
  const head = tick % length;
  return Array.from({ length }).map((_, index) => {
    const distance = Math.abs(index - head);
    if (distance === 0) {
      return `${color}◆${COLOR.reset}`;
    }
    if (distance === 1) {
      return `${COLOR.soft}◇${COLOR.reset}`;
    }
    return `${COLOR.secondary}·${COLOR.reset}`;
  }).join('');
}

function buildLoadingPanel(width: number, tick: number): string[] {
  const panelWidth = Math.max(42, Math.min(width, 72));
  const innerWidth = Math.max(24, panelWidth - 4);
  const orbit = ORBIT_FRAMES[tick % ORBIT_FRAMES.length] || ORBIT_FRAMES[0];
  const glyph = GLYPH_FRAMES[tick % GLYPH_FRAMES.length] || GLYPH_FRAMES[0];
  const pulseLeft = GLYPH_FRAMES[(tick + 1) % GLYPH_FRAMES.length] || GLYPH_FRAMES[0];
  const pulseRight = GLYPH_FRAMES[(tick + 3) % GLYPH_FRAMES.length] || GLYPH_FRAMES[0];
  const top = `${COLOR.soft}┌${'─'.repeat(panelWidth - 2)}┐${COLOR.reset}`;
  const bottom = `${COLOR.soft}└${'─'.repeat(panelWidth - 2)}┘${COLOR.reset}`;
  const line = (content = '') =>
    `${COLOR.soft}│${COLOR.reset} ${padRight(truncate(content, innerWidth), innerWidth)} ${COLOR.soft}│${COLOR.reset}`;

  const title = `${COLOR.accent}${COLOR.bold}${pulseLeft} Session Bootstrap ${pulseRight}${COLOR.reset}`;
  const orbitLine = `${COLOR.secondary}          ${COLOR.reset}${COLOR.soft}(${COLOR.reset} ${COLOR.accent}${orbit}${COLOR.reset} ${COLOR.soft})${COLOR.reset}          ${COLOR.secondary}${glyph}${COLOR.reset}`;
  const signalBar = buildSignalBar(Math.max(18, Math.floor(innerWidth * 0.72)), tick, COLOR.accent);
  const echoBar = buildSignalBar(Math.max(16, Math.floor(innerWidth * 0.58)), tick + 5, COLOR.soft);

  return [
    top,
    line(title),
    line(`${COLOR.secondary}Attaching thread, model and runtime snapshot${COLOR.reset}`),
    line(),
    line(orbitLine),
    line(`${COLOR.secondary}signal${COLOR.reset}   ${signalBar}`),
    line(`${COLOR.secondary}echo${COLOR.reset}     ${echoBar}`),
    line(`${COLOR.secondary}state${COLOR.reset}    ${COLOR.assistant}backend handshake in progress${COLOR.reset}`),
    line(`${COLOR.secondary}input${COLOR.reset}    ${COLOR.assistant}locked until thread is attached${COLOR.reset}`),
    line(),
    line(`${COLOR.soft}The shell opens after the first session snapshot arrives.${COLOR.reset}`),
    bottom,
  ];
}

export default function Transcript() {
  const { stdout } = useStdout();
  const { messages, selectedToolId, streaming, transcriptScroll, generating, threadId } = useAppState();
  const [loadingTick, setLoadingTick] = useState(0);

  useEffect(() => {
    if (threadId) {
      setLoadingTick(0);
      return;
    }
    const timer = setInterval(() => {
      setLoadingTick((current) => (current + 1) % 10_000);
    }, 120);
    return () => clearInterval(timer);
  }, [threadId]);

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
  const loadingPanel = buildLoadingPanel(Math.max(24, width - 4), loadingTick);
  const loadingTopSpacing = Math.max(1, Math.floor((visibleCount - loadingPanel.length) / 2));

  return (
    <Box flexDirection="column" paddingX={1} flexGrow={1}>
      {clampedOffset > 0 && (
        <Ansi>{`${COLOR.secondary}Showing older messages. Use PageUp/PageDown to scroll the in-app history.${COLOR.reset}`}</Ansi>
      )}
      <Box flexDirection="column" flexGrow={1} justifyContent="flex-end">
        {!threadId ? (
          <Box flexDirection="column">
            {Array.from({ length: loadingTopSpacing }).map((_, index) => (
              <Text key={`loading-space-${index}`}> </Text>
            ))}
            {loadingPanel.map((row, index) => (
              <Ansi key={`loading-row-${index}`}>{row}</Ansi>
            ))}
            <Text> </Text>
          </Box>
        ) : visible.length === 0 && !generating ? (
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
