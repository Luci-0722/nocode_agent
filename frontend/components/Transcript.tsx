import React, { useRef, useEffect } from 'react';
import { Box, Text, useStdout } from 'ink';
import { useAppState } from '../hooks/useAppState.js';
import Message from './Message.js';
import Ansi from './Ansi.js';

export default function Transcript() {
  const { messages, streaming } = useAppState();
  const { stdout } = useStdout();
  const scrollRef = useRef<number>(0);
  
  // 计算可用高度
  const terminalHeight = stdout.rows || 24;
  const headerHeight = 6;
  const composerHeight = 3;
  const statusBarHeight = 1;
  const availableHeight = terminalHeight - headerHeight - composerHeight - statusBarHeight;
  
  // 自动滚动到底部
  useEffect(() => {
    scrollRef.current = messages.length;
  }, [messages.length, streaming]);
  
  // 简单渲染所有消息（后续可优化为虚拟滚动）
  const visibleMessages = messages.slice(-availableHeight);
  
  return (
    <Box flexDirection="column" paddingX={1}>
      {visibleMessages.map((msg, index) => (
        <Message key={`${msg.id}-${index}`} message={msg} />
      ))}
      {streaming && (
        <Box flexDirection="column">
          <Ansi>{streaming}</Ansi>
        </Box>
      )}
    </Box>
  );
}