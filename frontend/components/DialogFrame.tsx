import React from 'react';
import { Box } from 'ink';
import { COLOR } from '../rendering.js';
import Ansi from './Ansi.js';

interface Props {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export default function DialogFrame({ title, subtitle, children }: Props) {
  return (
    <Box paddingX={1} marginBottom={1}>
      <Box flexDirection="column" borderStyle="round" borderColor="gray" paddingX={1} width="100%">
        <Ansi>{`${COLOR.accent}${COLOR.bold}${title}${COLOR.reset}`}</Ansi>
        {subtitle && <Ansi>{`${COLOR.secondary}${subtitle}${COLOR.reset}`}</Ansi>}
        <Box marginTop={1} flexDirection="column">
          {children}
        </Box>
      </Box>
    </Box>
  );
}
