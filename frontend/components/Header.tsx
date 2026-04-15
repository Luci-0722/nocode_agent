import React from 'react';
import { Box, Text } from 'ink';
import { useAppState } from '../hooks/useAppState.js';

export default function Header() {
  const { model, modelName, threadId, cwd } = useAppState();
  
  const shortCwd = cwd.length > 30 ? '...' + cwd.slice(-27) : cwd;
  const modelLabel = modelName || model || '-';
  
  return (
    <Box flexDirection="column" paddingX={1}>
      <Box>
        <Text bold color="cyan">
          █▀▀▄ █▀▀█ ▀▀█▀▀ ▀▀█▀▀ █▀▀ █▀▀█ █▀▀▀ 
        </Text>
      </Box>
      <Box>
        <Text bold color="cyan">
          █▄▄▀ █▄▄█   █     █   ▀▀█ █▄▄█ █▄▄▄ 
        </Text>
      </Box>
      <Box marginTop={1}>
        <Box width={20}>
          <Text dimColor>thread: </Text>
          <Text>{threadId ? threadId.slice(0, 8) : '-'}</Text>
        </Box>
        <Box width={30}>
          <Text dimColor>model: </Text>
          <Text>{modelLabel}</Text>
        </Box>
      </Box>
      <Box>
        <Text dimColor>cwd: </Text>
        <Text>{shortCwd}</Text>
      </Box>
    </Box>
  );
}