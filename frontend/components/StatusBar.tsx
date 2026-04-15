import React from 'react';
import { Box, Text } from 'ink';
import { useAppState } from '../hooks/useAppState.js';

export default function StatusBar() {
  const {
    generating,
    modelPickerOpen,
    permissionPreference,
    permissionRequest,
    questionRequest,
    threadId,
    tokensLeftPercent,
    transcriptScroll,
  } = useAppState();

  let hint = 'Enter send  Ctrl+J/K select tool  Ctrl+O expand  PgUp/PgDn scroll  Esc cancel';
  if (modelPickerOpen) {
    hint = 'Up/Down move  Enter select  Esc close';
  } else if (permissionRequest) {
    hint = 'Up/Down choose  Enter confirm';
  } else if (questionRequest) {
    hint = 'Up/Down choose  Space toggle  Enter submit';
  }

  return (
    <Box paddingX={1}>
      <Text dimColor>
        {threadId ? threadId.slice(0, 8) : '-'}  {tokensLeftPercent}% ctx  perm {permissionPreference}
        {generating ? '  generating' : ''}
        {transcriptScroll > 0 ? `  scroll ${transcriptScroll}` : ''}
        {'  '}
        {hint}
      </Text>
    </Box>
  );
}
