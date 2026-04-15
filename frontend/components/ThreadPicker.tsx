import React from 'react';
import { Box, Text } from 'ink';
import DialogFrame from './DialogFrame.js';
import { useAppState } from '../hooks/useAppState.js';

export default function ThreadPicker() {
  const { threadPickerIndex, threads } = useAppState();

  return (
    <DialogFrame title="Resume Session" subtitle="Up/Down move, Enter select, Esc close">
      {threads.length === 0 && <Text dimColor>No saved sessions.</Text>}
      {threads.map((thread, index) => {
        const selected = index === threadPickerIndex;
        return (
          <Box key={thread.thread_id} flexDirection="column" marginBottom={1}>
            <Box>
              <Text color={selected ? 'cyan' : undefined}>{selected ? '>' : ' '}</Text>
              <Text> </Text>
              <Text bold={selected}>{thread.thread_id.slice(0, 8)}</Text>
              <Text dimColor>{`  ${thread.message_count} msg`}</Text>
              {thread.source && <Text dimColor>{`  ${thread.source}`}</Text>}
            </Box>
            <Text dimColor>{thread.preview}</Text>
          </Box>
        );
      })}
    </DialogFrame>
  );
}
