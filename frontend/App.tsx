import React, { useState } from 'react';
import { Box, Text, useApp, useInput, useStdin } from 'ink';
import { useAppState } from './hooks/useAppState.js';
import { useBackend } from './hooks/useBackend.js';
import Header from './components/Header.js';
import Transcript from './components/Transcript.js';
import Composer from './components/Composer.js';
import StatusBar from './components/StatusBar.js';

export default function App() {
  const { exit } = useApp();
  const { stdin } = useStdin();
  const { generating, showModelPicker } = useAppState();
  const backend = useBackend();
  const [input, setInput] = useState('');
  
  // 检查是否支持 raw mode
  if (!stdin.isTTY) {
    return (
      <Box flexDirection="column">
        <Text color="red">Error: This program must be run in a terminal (TTY).</Text>
        <Text>Run with: ./nocode-ink</Text>
      </Box>
    );
  }
  
  // 全局快捷键
  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      exit();
    }
    // TODO: 添加更多快捷键
  });
  
  const handleSubmit = (text: string) => {
    if (!text.trim() || generating) return;
    backend.sendPrompt(text);
  };
  
  return (
    <Box flexDirection="column" height="100%">
      <Header />
      <Box flexGrow={1} flexDirection="column">
        <Transcript />
      </Box>
      <Composer
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        disabled={generating}
      />
      <StatusBar />
    </Box>
  );
}