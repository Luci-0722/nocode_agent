import React from 'react';
import { Box, Text } from 'ink';
import type { Message as MessageType } from '../hooks/useAppState.js';

interface Props {
  message: MessageType;
}

export default function Message({ message }: Props) {
  switch (message.kind) {
    case 'user':
      return (
        <Box marginTop={1} flexDirection="column">
          <Box>
            <Text bold color="cyan">{'>'} </Text>
            <Text>{message.content}</Text>
          </Box>
        </Box>
      );
      
    case 'assistant':
      return (
        <Box marginTop={1} flexDirection="column">
          <Text>{message.content}</Text>
        </Box>
      );
      
    case 'system':
      return (
        <Box marginTop={1}>
          <Text dimColor italic>{message.content}</Text>
        </Box>
      );
      
    case 'tool':
      return <ToolMessage message={message} />;
      
    case 'subagent':
      return <SubagentMessage message={message} />;
      
    default:
      return null;
  }
}

function ToolMessage({ message }: Props) {
  const statusColor = message.status === 'running' ? 'yellow' : message.status === 'error' ? 'red' : 'green';
  const statusIcon = message.status === 'running' ? '⏳' : message.status === 'error' ? '✗' : '✓';
  
  return (
    <Box marginTop={1} flexDirection="column">
      <Box>
        <Text color={statusColor}>{statusIcon} </Text>
        <Text bold color="blue">{message.name}</Text>
        {message.status === 'running' && <Text dimColor> running...</Text>}
      </Box>
      {message.args && Object.keys(message.args).length > 0 && (
        <Box marginLeft={2}>
          <Text dimColor>{JSON.stringify(message.args, null, 2).slice(0, 200)}</Text>
        </Box>
      )}
      {message.output && (
        <Box marginLeft={2} flexDirection="column">
          <Text dimColor>{message.output.slice(0, 500)}</Text>
        </Box>
      )}
    </Box>
  );
}

function SubagentMessage({ message }: Props) {
  return (
    <Box marginTop={1} flexDirection="column">
      <Box>
        <Text color="magenta">◇ </Text>
        <Text bold>{message.subagent_type}</Text>
        <Text dimColor> (subagent)</Text>
      </Box>
      {message.content && (
        <Box marginLeft={2}>
          <Text dimColor>{message.content.slice(0, 300)}</Text>
        </Box>
      )}
    </Box>
  );
}