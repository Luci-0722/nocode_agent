import React from 'react';
import { Box, Text } from 'ink';
import { useAppState } from '../hooks/useAppState.js';

function shorten(text: string, max: number): string {
  return text.length > max ? `...${text.slice(-(max - 3))}` : text;
}

export default function Header() {
  const { cwd, model, modelName, reasoningEffort, subagentModel, threadId } = useAppState();
  const modelLabel = modelName ? `${modelName} (${model})` : model || '-';

  return (
    <Box flexDirection="column" paddingX={1} marginBottom={1}>
      <Box>
        <Text color="cyan" bold>
          NoCode
        </Text>
        <Text dimColor> ink repl</Text>
      </Box>
      <Box>
        <Text dimColor>thread: </Text>
        <Text>{threadId ? threadId.slice(0, 8) : '-'}</Text>
        <Text dimColor>  model: </Text>
        <Text>{shorten(modelLabel, 34)}</Text>
        <Text dimColor>  effort: </Text>
        <Text>{reasoningEffort || '-'}</Text>
      </Box>
      <Box>
        <Text dimColor>cwd: </Text>
        <Text>{shorten(cwd || '-', 56)}</Text>
        <Text dimColor>  subagent: </Text>
        <Text>{shorten(subagentModel || '-', 18)}</Text>
      </Box>
    </Box>
  );
}
