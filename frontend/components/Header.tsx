import React from 'react';
import { Box, Text, useStdout } from 'ink';
import { useAppState } from '../hooks/useAppState.js';
import { COLOR, tildePath, truncate, visibleLength } from '../rendering.js';
import Ansi from './Ansi.js';

const LOGO = ['█▄  █  ▄██▄', '█ ▀ █  █  █', '▀   ▀  ▀██▀'];

export default function Header() {
  const { stdout } = useStdout();
  const { cwd, model, modelName, reasoningEffort, threadId } = useAppState();
  const width = Math.max(40, (stdout.columns || 80) - 2);
  const logoWidth = visibleLength(LOGO[0] || '');
  const rightWidth = Math.max(12, width - logoWidth - 2);
  const modelDisplay = modelName ? `${modelName} (${model})` : model;

  const lines = [
    `${COLOR.accent}${COLOR.bold}${LOGO[0]}${COLOR.reset}  ${COLOR.secondary}${truncate(`thread: ${threadId.slice(-8) || '--------'}`, rightWidth)}${COLOR.reset}`,
    `${COLOR.accent}${COLOR.bold}${LOGO[1]}${COLOR.reset}  ${COLOR.secondary}${truncate(`model: ${[modelDisplay, reasoningEffort].filter(Boolean).join(' ') || '-'}`, rightWidth)}${COLOR.reset}`,
    `${COLOR.accent}${COLOR.bold}${LOGO[2]}${COLOR.reset}  ${COLOR.secondary}${truncate(`cwd: ${tildePath(cwd || '-')}`, rightWidth)}${COLOR.reset}`,
  ];

  return (
    <Box flexDirection="column" paddingX={1} marginBottom={1}>
      {lines.map((line, index) => (
        <Ansi key={index}>{line}</Ansi>
      ))}
      <Text> </Text>
    </Box>
  );
}
