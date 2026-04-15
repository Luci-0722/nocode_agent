import React, { useRef, useState } from 'react';
import { Box, Text, useInput, useStdin } from 'ink';

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  disabled?: boolean;
}

export default function Composer({ value, onChange, onSubmit, disabled = false }: Props) {
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const savedValueRef = useRef('');
  const { stdin } = useStdin();

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
        onChange(history[history.length - 1 - nextIndex]);
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
        onChange(history[history.length - 1 - nextIndex]);
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
        const next = value.replace(/\s*\S+\s*$/, '');
        onChange(next);
        setHistoryIndex(-1);
        return;
      }

      if (input && !key.ctrl && !key.meta && input.length === 1 && input.charCodeAt(0) >= 32) {
        onChange(value + input);
        setHistoryIndex(-1);
      }
    },
    { isActive: stdin.isTTY },
  );

  return (
    <Box flexDirection="column" paddingX={1} marginTop={1}>
      <Box borderStyle="round" borderColor={disabled ? 'gray' : 'cyan'} paddingX={1}>
        <Text color="cyan">{'>'} </Text>
        <Box flexGrow={1}>
          <Text>{value}</Text>
          {!disabled && <Text backgroundColor="cyan"> </Text>}
        </Box>
      </Box>
      <Text dimColor>
        {disabled ? 'Input paused while dialog is open or generation is running.' : 'Slash commands: /help /models /resume /permission ask|all'}
      </Text>
    </Box>
  );
}
