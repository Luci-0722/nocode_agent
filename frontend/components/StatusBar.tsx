import React from 'react';
import { Box, Text } from 'ink';
import { useAppState } from '../hooks/useAppState.js';

export default function StatusBar() {
  const { generating } = useAppState();
  
  return (
    <Box>
      {generating && (
        <Text dimColor>Generating... </Text>
      )}
      <Text dimColor>Ctrl+C to exit</Text>
    </Box>
  );
}