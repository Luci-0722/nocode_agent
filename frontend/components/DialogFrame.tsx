import React from 'react';
import { Box, Text } from 'ink';

interface Props {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export default function DialogFrame({ title, subtitle, children }: Props) {
  return (
    <Box paddingX={1} marginBottom={1}>
      <Box flexDirection="column" borderStyle="round" borderColor="cyan" paddingX={1} width="100%">
        <Text bold color="cyan">
          {title}
        </Text>
        {subtitle && <Text dimColor>{subtitle}</Text>}
        <Box marginTop={1} flexDirection="column">
          {children}
        </Box>
      </Box>
    </Box>
  );
}
