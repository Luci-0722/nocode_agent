import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Box, useInput, useStdin, useStdout } from 'ink';
import { useAppState } from '../hooks/useAppState.js';
import {
  COLOR,
  formatDuration,
  GENERATING_SPINNER_FRAMES,
  padRight,
  truncate,
  truncateAnsiAware,
  visibleLength,
  wrap,
} from '../rendering.js';
import { getSlashCommandSuggestions, type SlashCommandDefinition } from '../slashCommands.js';
import Ansi from './Ansi.js';

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  disabled?: boolean;
}

interface ActiveSlashMenu {
  query: string;
  suggestions: SlashCommandDefinition[];
}

function isPrintableInput(input: string, key: { ctrl?: boolean; meta?: boolean }): boolean {
  return Boolean(input) && !key.ctrl && !key.meta && !/[\u0000-\u001f\u007f]/.test(input);
}

function getActiveSlashCommandMenu(input: string): ActiveSlashMenu | null {
  if (!input.startsWith('/') || input.includes('\n')) {
    return null;
  }

  const afterSlash = input.slice(1);
  if (/\s/.test(afterSlash)) {
    return null;
  }

  const query = afterSlash.toLowerCase();
  const suggestions = getSlashCommandSuggestions(query);
  if (suggestions.length === 0) {
    return null;
  }
  return { query, suggestions };
}

function renderSelectedRow(content: string, width: number, marker = '▸'): string {
  const inner = `${COLOR.selectedBorder}${COLOR.bold}${marker} ${COLOR.reset}${content}`;
  return `${COLOR.selectedBg}${padRight(inner, width)}${COLOR.reset}`;
}

export default function Composer({ value, onChange, onSubmit, disabled = false }: Props) {
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [tick, setTick] = useState(0);
  const [slashIndex, setSlashIndex] = useState(0);
  const savedValueRef = useRef('');
  const lastSlashQueryRef = useRef('');
  const { stdin } = useStdin();
  const { stdout } = useStdout();
  const { generating, generatingStartedAt } = useAppState();

  useEffect(() => {
    if (!generating) {
      return;
    }
    const timer = setInterval(() => {
      setTick((current) => current + 1);
    }, 80);
    return () => clearInterval(timer);
  }, [generating]);

  const activeSlashMenu = useMemo(() => getActiveSlashCommandMenu(value), [value]);

  useEffect(() => {
    if (!activeSlashMenu) {
      lastSlashQueryRef.current = '';
      setSlashIndex(0);
      return;
    }
    if (lastSlashQueryRef.current !== activeSlashMenu.query) {
      lastSlashQueryRef.current = activeSlashMenu.query;
      setSlashIndex(0);
      return;
    }
    if (slashIndex >= activeSlashMenu.suggestions.length) {
      setSlashIndex(Math.max(0, activeSlashMenu.suggestions.length - 1));
    }
  }, [activeSlashMenu, slashIndex]);

  const applySelectedSlashCommand = (forceApply: boolean): boolean => {
    if (!activeSlashMenu) {
      return false;
    }

    const selected = activeSlashMenu.suggestions[slashIndex];
    if (!selected) {
      return false;
    }

    const currentToken = value.slice(1).trim().toLowerCase();
    const isExactMatch =
      currentToken === selected.name || selected.aliases?.includes(currentToken) || false;
    if (!forceApply && isExactMatch) {
      return false;
    }

    const nextValue = `/${selected.name}${selected.acceptsArgs ? ' ' : ''}`;
    onChange(nextValue);
    return true;
  };

  useInput(
    (input, key) => {
      if (disabled) {
        return;
      }

      if (key.upArrow) {
        if (activeSlashMenu) {
          setSlashIndex((current) => Math.max(0, current - 1));
          return;
        }
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
        if (activeSlashMenu) {
          setSlashIndex((current) =>
            Math.min(activeSlashMenu.suggestions.length - 1, current + 1),
          );
          return;
        }
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
        if (applySelectedSlashCommand(false)) {
          return;
        }
        setHistory((previous) => [...previous.slice(-49), value]);
        setHistoryIndex(-1);
        savedValueRef.current = '';
        onSubmit(value);
        return;
      }

      if (key.tab || input === '\t') {
        if (applySelectedSlashCommand(true)) {
          return;
        }
        onChange(`${value}  `);
        setHistoryIndex(-1);
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
    composerLines[composerLines.length - 1] =
      `${composerLines[composerLines.length - 1]}${COLOR.user}${COLOR.bold}▋${COLOR.reset}`;
  }

  const slashMenuLines = (() => {
    if (!activeSlashMenu) {
      return [];
    }

    const maxVisibleItems = 5;
    const startIndex = Math.max(
      0,
      Math.min(
        slashIndex - Math.floor(maxVisibleItems / 2),
        activeSlashMenu.suggestions.length - maxVisibleItems,
      ),
    );
    const endIndex = Math.min(activeSlashMenu.suggestions.length, startIndex + maxVisibleItems);
    const nameWidth = Math.max(10, Math.min(Math.floor(width * 0.4), Math.max(10, width - 6)));
    const lines: string[] = [];

    for (let index = startIndex; index < endIndex; index += 1) {
      const command = activeSlashMenu.suggestions[index];
      if (!command) {
        continue;
      }
      const selected = index === slashIndex;
      const label = `/${command.name}${command.argumentHint ? ` ${command.argumentHint}` : ''}`;
      const paddedLabel = padRight(
        `${COLOR.accent}${COLOR.bold}${label}${COLOR.reset}`,
        Math.min(nameWidth, Math.max(10, width - 4)),
      );
      const descriptionWidth = Math.max(0, width - visibleLength(paddedLabel) - 4);
      const description =
        descriptionWidth > 0
          ? `${COLOR.soft}${truncate(command.description, descriptionWidth)}${COLOR.reset}`
          : '';
      const content = description ? `${paddedLabel}  ${description}` : paddedLabel;
      const visibleContent = truncateAnsiAware(content, Math.max(10, width - 2));
      lines.push(selected ? renderSelectedRow(visibleContent, width, '▸') : `  ${visibleContent}`);
    }

    return lines;
  })();

  const elapsedMs = generating && generatingStartedAt > 0 ? Date.now() - generatingStartedAt : 0;
  const elapsedSeconds = Math.max(0, Math.floor(elapsedMs / 1000));
  const spinnerFrame =
    GENERATING_SPINNER_FRAMES[Math.floor(elapsedMs / 80) % GENERATING_SPINNER_FRAMES.length] ||
    GENERATING_SPINNER_FRAMES[0];
  void tick;

  return (
    <Box flexDirection="column" paddingX={1} marginTop={1}>
      {slashMenuLines.map((line, index) => (
        <Ansi key={`slash-${index}`}>{line}</Ansi>
      ))}
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
