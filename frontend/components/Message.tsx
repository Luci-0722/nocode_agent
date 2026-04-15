import React from 'react';
import { Box, Text } from 'ink';
import type { Message as MessageType, ToolMessage } from '../hooks/useAppState.js';
import Ansi, { stripAnsi } from './Ansi.js';

interface Props {
  message: MessageType;
  selected?: boolean;
}

function pretty(value: unknown): string {
  if (typeof value === 'string') {
    return value;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function TextMessage({ message }: { message: Extract<MessageType, { kind: 'message' }> }) {
  if (message.role === 'user') {
    return (
      <Box flexDirection="column" marginBottom={1}>
        <Box>
          <Text color="green" bold>
            User
          </Text>
          {message.state === 'queued' && <Text dimColor> queued</Text>}
        </Box>
        <Ansi>{message.content}</Ansi>
      </Box>
    );
  }

  if (message.role === 'assistant') {
    return (
      <Box flexDirection="column" marginBottom={1}>
        <Text color="cyan" bold>
          Assistant
        </Text>
        <Ansi>{message.content}</Ansi>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text dimColor>System</Text>
      <Text dimColor>{stripAnsi(message.content)}</Text>
    </Box>
  );
}

function ToolDetails({ message }: { message: ToolMessage }) {
  return (
    <Box flexDirection="column" marginLeft={2} marginTop={1}>
      {message.args && (
        <Box flexDirection="column" marginBottom={1}>
          <Text dimColor>args</Text>
          <Text>{pretty(message.args)}</Text>
        </Box>
      )}
      {message.output && (
        <Box flexDirection="column" marginBottom={1}>
          <Text dimColor>output</Text>
          <Ansi>{message.output}</Ansi>
        </Box>
      )}
      {(message.subagents || []).map((subagent) => (
        <Box key={subagent.id} flexDirection="column" marginBottom={1}>
          <Text color="magenta">
            subagent {subagent.subagent_type} {subagent.status === 'done' ? 'done' : 'running'}
          </Text>
          {subagent.summary && <Text dimColor>{subagent.summary}</Text>}
          {subagent.tool_calls.map((toolCall) => (
            <Text key={`${subagent.id}-${toolCall.id}`} dimColor>
              - {toolCall.name} {toolCall.status}
            </Text>
          ))}
        </Box>
      ))}
    </Box>
  );
}

function ToolBlock({ message, selected = false }: { message: ToolMessage; selected?: boolean }) {
  const statusColor = message.status === 'running' ? 'yellow' : 'green';
  const title = `${message.name}${message.status === 'running' ? ' running' : ' done'}`;

  return (
    <Box
      flexDirection="column"
      marginBottom={1}
      borderStyle="round"
      borderColor={selected ? 'cyan' : 'gray'}
      paddingX={1}
    >
      <Box>
        <Text color={statusColor}>{message.status === 'running' ? '●' : '✓'}</Text>
        <Text> </Text>
        <Text bold color={selected ? 'cyan' : 'blue'}>
          {title}
        </Text>
      </Box>
      {!message.expanded && message.output && (
        <Text dimColor>{stripAnsi(message.output).slice(0, 160)}</Text>
      )}
      {message.expanded && <ToolDetails message={message} />}
    </Box>
  );
}

export default function Message({ message, selected = false }: Props) {
  if (message.kind === 'message') {
    return <TextMessage message={message} />;
  }
  return <ToolBlock message={message} selected={selected} />;
}
