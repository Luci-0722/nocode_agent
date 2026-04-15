import React, { useEffect, useRef, useState } from 'react';
import { Box, useInput, useStdin, useStdout } from 'ink';
import { useAppState } from '../hooks/useAppState.js';
import {
  COLOR,
  formatDuration,
  GENERATING_SPINNER_FRAMES,
  truncate,
  wrap,
} from '../rendering.js';
import Ansi from './Ansi.js';

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  disabled?: boolean;
}

function isPrintableInput(input: string, key: { ctrl?: boolean; meta?: boolean }): boolean {
  return Boolean(input) && !key.ctrl && !key.meta && !/[\u0000-\u001f\u007f]/.test(input);
}

export default function Composer({ value, onChange, onSubmit, disabled = false }: Props) {
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [tick, setTick] = useState(0);
  const savedValueRef = useRef('');
  const { stdin } = useStdin();
  const { stdout } = useStdout();
  const { generating, generatingStartedAt } = useAppState();

  useEffect(() => {
    if (!generating) {
      return;
    }
    const timer = setInterval(() => {
      setTick((value) => value + 1);
    }, 80);
    return () => clearInterval(timer);
  }, [generating]);

  useInput(
    (input, key) => {
      if (disabled) {
        return;
      }

      if (key.upArrow) {
        if (history.length === 0) {
          return;
        }
        if (historyIndex === -1) {
          savedValueRef.current = value;
        }
        const nextIndex = Math.min(history.length - 1, historyIndex + 1);
        setHistoryIndex(nextIndex);
        onChange(history[history.length - 1 - nextIndex] || '');
        return;
      }

      if (key.downArrow) {
        if (historyIndex <= 0) {
          setHistoryIndex(-1);
          onChange(savedValueRef.current);
          return;
        }
        const nextIndex = historyIndex - 1;
        setHistoryIndex(nextIndex);
        onChange(history[history.length - 1 - nextIndex] || '');
        return;
      }

      if (key.return && key.shift) {
        onChange(`${value}\n`);
        setHistoryIndex(-1);
        return;
      }

      if (key.return) {
        if (!value.trim()) {
          return;
        }
        setHistory((previous) => [...previous.slice(-49), value]);
        setHistoryIndex(-1);
        savedValueRef.current = '';
        onSubmit(value);
        return;
      }

      if (key.backspace || key.delete) {
        onChange(value.slice(0, -1));
        setHistoryIndex(-1);
        return;
      }

      if (key.ctrl && input === 'u') {
        onChange('');
        setHistoryIndex(-1);
        return;
      }

      if (key.ctrl && input === 'w') {
        onChange(value.replace(/\s*\S+\s*$/, ''));
        setHistoryIndex(-1);
        return;
      }

      if (isPrintableInput(input, key)) {
        onChange(value + input);
        setHistoryIndex(-1);
      }
    },
    { isActive: stdin.isTTY },
  );

  const width = Math.max(24, (stdout.columns || 80) - 2);
  const separator = `${COLOR.secondary}${'─'.repeat(width)}${COLOR.reset}`;
  const availableWidth = Math.max(12, width - 4);
  const body = value.length > 0 ? value.split('\n') : [''];
  const wrappedLines = body.flatMap((line, lineIndex) => {
    const segments = wrap(line, availableWidth);
    return segments.map((segment, segmentIndex) => {
      const prefix = lineIndex === 0 && segmentIndex === 0 ? '❯ ' : '  ';
      return `${COLOR.user}${COLOR.bold}${prefix}${COLOR.reset}${segment}`;
    });
  });

  if (wrappedLines.length === 0) {
    wrappedLines.push(`${COLOR.user}${COLOR.bold}❯ ${COLOR.reset}`);
  }
  const composerLines = [...wrappedLines];
  if (!disabled) {
    composerLines[composerLines.length - 1] = `${composerLines[composerLines.length - 1]}${COLOR.user}${COLOR.bold}▋${COLOR.reset}`;
  }

  const elapsedMs = generating && generatingStartedAt > 0 ? Date.now() - generatingStartedAt : 0;
  const elapsedSeconds = Math.max(0, Math.floor(elapsedMs / 1000));
  const spinnerFrame =
    GENERATING_SPINNER_FRAMES[Math.floor(elapsedMs / 80) % GENERATING_SPINNER_FRAMES.length] ||
    GENERATING_SPINNER_FRAMES[0];
  void tick;

  return (
    <Box flexDirection="column" paddingX={1} marginTop={1}>
      {generating && (
        <Ansi>
          {truncate(
            `${COLOR.warning}${COLOR.bold}${spinnerFrame}${COLOR.reset} ${COLOR.bold}Generating${COLOR.reset} ${COLOR.secondary}(${formatDuration(elapsedSeconds)} • esc to interrupt)${COLOR.reset}`,
            width,
          )}
        </Ansi>
      )}
      <Ansi>{separator}</Ansi>
      {composerLines.map((line, index) => (
        <Ansi key={index}>{line}</Ansi>
      ))}
    </Box>
  );
}
