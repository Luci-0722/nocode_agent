import React, { useState, useRef, useEffect } from 'react';
import { Box, Text, useInput, useStdin } from 'ink';

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  disabled?: boolean;
}

export default function Composer({ value, onChange, onSubmit, disabled }: Props) {
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const savedValueRef = useRef<string>('');
  const { stdin } = useStdin();
  
  // 处理键盘输入
  useInput(
    (input, key) => {
      if (disabled) return;
      
      // 上箭头：历史记录向上
      if (key.upArrow) {
        if (history.length > 0) {
          if (historyIndex === -1) {
            savedValueRef.current = value;
          }
          const newIndex = Math.min(historyIndex + 1, history.length - 1);
          setHistoryIndex(newIndex);
          onChange(history[history.length - 1 - newIndex]);
        }
        return;
      }
      
      // 下箭头：历史记录向下
      if (key.downArrow) {
        if (historyIndex > 0) {
          const newIndex = historyIndex - 1;
          setHistoryIndex(newIndex);
          onChange(history[history.length - 1 - newIndex]);
        } else if (historyIndex === 0) {
          setHistoryIndex(-1);
          onChange(savedValueRef.current);
        }
        return;
      }
      
      // 回车：提交
      if (key.return) {
        if (value.trim()) {
          setHistory((prev) => [...prev.slice(-50), value]); // 保留最近 50 条
          setHistoryIndex(-1);
          onSubmit(value);
        }
        return;
      }
      
      // Backspace/Delete：删除字符
      if (key.backspace || key.delete) {
        onChange(value.slice(0, -1));
        setHistoryIndex(-1);
        return;
      }
      
      // Ctrl+U：清空输入
      if (key.ctrl && input === 'u') {
        onChange('');
        setHistoryIndex(-1);
        return;
      }
      
      // Ctrl+W：删除最后一个单词
      if (key.ctrl && input === 'w') {
        const lastSpace = value.lastIndexOf(' ');
        onChange(lastSpace >= 0 ? value.slice(0, lastSpace) : '');
        setHistoryIndex(-1);
        return;
      }
      
      // 其他可打印字符：添加到输入
      if (input && !key.ctrl && !key.meta && input.length === 1 && input.charCodeAt(0) >= 32) {
        onChange(value + input);
        setHistoryIndex(-1);
        return;
      }
    },
    { isActive: !disabled && stdin.isTTY }
  );
  
  // 显示输入框
  const displayValue = value || '';
  const cursorChar = disabled ? '' : '█';
  
  return (
    <Box borderStyle="single" borderColor={disabled ? 'gray' : 'cyan'} paddingX={1}>
      <Text color="cyan" bold>{'>'} </Text>
      <Box flexGrow={1}>
        <Text>{displayValue}</Text>
        {!disabled && <Text backgroundColor="cyan">{cursorChar}</Text>}
      </Box>
      {disabled && <Text dimColor> generating...</Text>}
    </Box>
  );
}