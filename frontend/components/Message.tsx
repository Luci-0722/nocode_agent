import React from 'react';
import { Box, Text } from 'ink';
import type { Message as MessageType, ToolMessage } from '../hooks/useAppState.js';
import type { SubagentToolCall } from '../types/events.js';
import Ansi, { stripAnsi } from './Ansi.js';

interface Props {
  message: MessageType;
  selected?: boolean;
}

type TodoArg = {
  content?: unknown;
  status?: unknown;
};

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

function excerpt(text: string, maxLength = 160): string {
  const singleLine = stripAnsi(text).replace(/\s+/g, ' ').trim();
  if (singleLine.length <= maxLength) {
    return singleLine;
  }
  return `${singleLine.slice(0, maxLength - 3)}...`;
}

function getStringArg(args: Record<string, unknown> | undefined, ...keys: string[]): string {
  for (const key of keys) {
    const value = args?.[key];
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }
  return '';
}

function getTodoSummary(tool: ToolMessage): string[] {
  const rawTodos = tool.args?.todos;
  if (!Array.isArray(rawTodos)) {
    return [];
  }

  return rawTodos
    .slice(0, 4)
    .map((item) => item as TodoArg)
    .filter((item) => typeof item?.content === 'string' && item.content.trim())
    .map((item) => {
      const status = item.status === 'completed' ? 'done' : item.status === 'in_progress' ? 'doing' : 'todo';
      return `${status}: ${String(item.content).trim()}`;
    });
}

function getPlanSummary(tool: ToolMessage): string[] {
  const rawPlan = tool.args?.plan;
  if (!Array.isArray(rawPlan)) {
    return [];
  }

  return rawPlan
    .slice(0, 4)
    .map((step) => {
      if (!step || typeof step !== 'object') {
        return '';
      }
      const record = step as Record<string, unknown>;
      const label = typeof record.step === 'string' ? record.step.trim() : '';
      const status = typeof record.status === 'string' ? record.status.trim() : '';
      return label ? `${status || 'pending'}: ${label}` : '';
    })
    .filter(Boolean);
}

function getToolSummaryLines(tool: ToolMessage): string[] {
  const command = getStringArg(tool.args, 'cmd', 'command');
  if (command) {
    return [command];
  }

  const path = getStringArg(tool.args, 'path', 'file_path', 'filename', 'ref_id');
  if (path) {
    return [path];
  }

  if (tool.name === 'todo_write') {
    const todos = getTodoSummary(tool);
    if (todos.length > 0) {
      return todos;
    }
  }

  if (tool.name === 'update_plan') {
    const plan = getPlanSummary(tool);
    if (plan.length > 0) {
      return plan;
    }
  }

  if (tool.name === 'ask_user_question') {
    const questions = Array.isArray(tool.args?.questions) ? tool.args.questions.length : 0;
    return [`${questions || 1} question${questions === 1 ? '' : 's'}`];
  }

  if (tool.output) {
    return [excerpt(tool.output)];
  }

  return [];
}

function getToolOutcomeLabel(tool: ToolMessage): string {
  if (tool.status === 'running') {
    return 'running';
  }
  if (!tool.output) {
    return 'done';
  }
  const text = stripAnsi(tool.output).trim();
  if (!text) {
    return 'done';
  }
  return excerpt(text, 80);
}

function renderKeyValue(label: string, value: unknown) {
  const text = pretty(value);
  return (
    <Box flexDirection="column" marginBottom={1} key={label}>
      <Text dimColor>{label}</Text>
      <Ansi>{text}</Ansi>
    </Box>
  );
}

function renderSubagentTool(toolCall: SubagentToolCall) {
  const summary = toolCall.output ? excerpt(toolCall.output, 120) : '';
  return (
    <Box key={`${toolCall.id}-${toolCall.name}`} flexDirection="column" marginBottom={1}>
      <Text dimColor>
        - {toolCall.name} {toolCall.status}
      </Text>
      {summary && <Text dimColor>{summary}</Text>}
    </Box>
  );
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
      <Ansi>{message.content}</Ansi>
    </Box>
  );
}

function ToolDetails({ message }: { message: ToolMessage }) {
  const summaryLines = getToolSummaryLines(message);
  return (
    <Box flexDirection="column" marginLeft={2} marginTop={1}>
      {summaryLines.length > 0 && (
        <Box flexDirection="column" marginBottom={1}>
          <Text dimColor>summary</Text>
          {summaryLines.map((line, index) => (
            <Text key={`${message.id}-summary-${index}`}>{line}</Text>
          ))}
        </Box>
      )}
      {message.args && Object.keys(message.args).length > 0 && renderKeyValue('args', message.args)}
      {message.output && renderKeyValue('output', message.output)}
      {(message.subagents || []).map((subagent) => (
        <Box key={subagent.id} flexDirection="column" marginBottom={1}>
          <Text color="magenta">
            subagent {subagent.subagent_type} {subagent.status === 'done' ? 'done' : 'running'}
          </Text>
          <Text dimColor>{subagent.thread_id}</Text>
          {subagent.summary && <Text>{excerpt(subagent.summary, 180)}</Text>}
          {subagent.tool_calls.map(renderSubagentTool)}
        </Box>
      ))}
    </Box>
  );
}

function ToolBlock({ message, selected = false }: { message: ToolMessage; selected?: boolean }) {
  const statusColor = message.status === 'running' ? 'yellow' : 'green';
  const statusIcon = message.status === 'running' ? '●' : '✓';
  const summaryLines = getToolSummaryLines(message);

  return (
    <Box
      flexDirection="column"
      marginBottom={1}
      borderStyle="round"
      borderColor={selected ? 'cyan' : 'gray'}
      paddingX={1}
    >
      <Box>
        <Text color={statusColor}>{statusIcon}</Text>
        <Text> </Text>
        <Text bold color={selected ? 'cyan' : 'blue'}>
          {message.name}
        </Text>
        <Text dimColor>{`  ${getToolOutcomeLabel(message)}`}</Text>
        {selected && <Text color="cyan">  selected</Text>}
      </Box>
      {!message.expanded && summaryLines.length > 0 && (
        <Box flexDirection="column">
          {summaryLines.slice(0, 3).map((line, index) => (
            <Text key={`${message.id}-collapsed-${index}`} dimColor>
              {line}
            </Text>
          ))}
        </Box>
      )}
      {!message.expanded && selected && (
        <Text dimColor>Ctrl+O expands this tool.</Text>
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
