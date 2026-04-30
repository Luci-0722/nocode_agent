import type { Message, ToolMessage } from './hooks/useAppState.js';
import type { SubagentToolCall } from './types/events.js';
import {
  COLOR,
  padRight,
  renderMarkdownLines,
  stripAnsi,
  truncate,
  truncateAnsiAware,
  UI_GLYPHS,
  visibleLength,
  wrap,
  wrapAnsiAware,
} from './rendering.js';

type TodoArg = {
  content?: unknown;
  status?: unknown;
};

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

function formatValue(value: unknown): string {
  if (typeof value === 'string') {
    return JSON.stringify(truncate(value, 40));
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => formatValue(item)).join(', ')}]`;
  }
  if (value && typeof value === 'object') {
    try {
      return truncate(JSON.stringify(value), 64);
    } catch {
      return '{...}';
    }
  }
  return String(value);
}

function formatToolArgs(args: Record<string, unknown>): string {
  return Object.entries(args)
    .map(([key, value]) => `${key}=${formatValue(value)}`)
    .join(', ');
}

function describeToolArgs(tool: ToolMessage): string {
  if (!tool.args || Object.keys(tool.args).length === 0) {
    return '';
  }
  if (tool.name === 'ask_user_question') {
    const questions = Array.isArray(tool.args.questions) ? tool.args.questions.length : 0;
    return `提出 ${questions || 1} 个问题`;
  }
  return `(${formatToolArgs(tool.args)})`;
}

function describeTool(tool: ToolMessage): string {
  const argSummary = describeToolArgs(tool);
  return argSummary ? `${tool.name} ${argSummary}` : tool.name;
}

function describeToolOutcome(tool: ToolMessage): string {
  if (tool.status === 'running') {
    return `${COLOR.warning}执行中...${COLOR.reset}`;
  }
  return `${COLOR.secondary}已完成${COLOR.reset}`;
}

function formatToolSummary(tool: ToolMessage, width: number): string {
  return truncateAnsiAware(`${describeTool(tool)}  ${describeToolOutcome(tool)}`, width);
}

function renderUserStateTag(line: string, state?: 'queued' | 'sent'): string {
  if (state === 'queued') {
    return `${line} ${COLOR.warning}[queued]${COLOR.reset}${COLOR.bold}`;
  }
  return line;
}

function styleToolRow(content: string, width: number, selected: boolean): string {
  const preservedBgContent = content.replace(/\x1b\[0m/g, '\x1b[39m\x1b[22m');
  if (!selected) {
    return preservedBgContent;
  }
  return `${COLOR.selectedBg}${padRight(preservedBgContent, width)}${COLOR.reset}`;
}

function renderSubagentTool(toolCall: SubagentToolCall, width: number): string[] {
  const availableWidth = Math.max(12, width - 8);
  const toolStatus =
    toolCall.status === 'running'
      ? `${COLOR.warning}执行中...${COLOR.reset}`
      : `${COLOR.secondary}${excerpt(toolCall.output || '已完成', availableWidth - 12)}${COLOR.reset}`;
  const text = `${toolCall.name}${toolCall.args && Object.keys(toolCall.args).length > 0 ? ` (${formatToolArgs(toolCall.args)})` : ''}  ${toolStatus}`;
  return wrapAnsiAware(text, availableWidth).map((line) => `      ${line}`);
}

function renderTextMessageLines(message: Extract<Message, { kind: 'message' }>, width: number): string[] {
  const availableWidth = Math.max(12, message.role === 'system' ? width : width - 4);

  if (message.role === 'assistant') {
    return renderMarkdownLines(message.content || ' ', availableWidth).map((line, index) => {
      const leader = index === 0 ? UI_GLYPHS.assistantLeader : '  ';
      return `${COLOR.accent}${leader}${COLOR.reset}${line}`;
    });
  }

  if (message.role === 'system') {
    return (message.content || ' ')
      .split('\n')
      .flatMap((rawLine) => {
        const expandedLines = /^日志文件:\s+/.test(rawLine)
          ? [
              { text: '日志文件:', prefix: '  ' },
              { text: rawLine.replace(/^日志文件:\s+/, ''), prefix: '' },
            ]
          : [{ text: rawLine, prefix: '  ' }];
        return expandedLines.flatMap(({ text, prefix }) => {
          const segments = wrap(text, Math.max(12, availableWidth - prefix.length));
          return segments.map((segment) => `${COLOR.secondary}${prefix}${segment}${COLOR.reset}`);
        });
      });
  }

  return wrap(message.content || ' ', availableWidth).map((line, index) => {
    const leader = index === 0 ? (message.role === 'user' ? UI_GLYPHS.userLeader : '  ') : '  ';
    const contentWithState =
      message.role === 'user' && index === 0 ? renderUserStateTag(line, message.state) : line;
    const body =
      message.role === 'user'
        ? `${COLOR.bold}${contentWithState}${COLOR.reset}`
        : `${COLOR.secondary}${line}${COLOR.reset}`;
    const marker =
      message.role === 'user'
        ? `${COLOR.user}${COLOR.bold}${leader}${COLOR.reset}`
        : `${COLOR.secondary}${leader}${COLOR.reset}`;
    return `${marker}${body}`;
  });
}

function renderToolDetails(message: ToolMessage, width: number, selected: boolean): string[] {
  const lines: string[] = [];
  const availableWidth = Math.max(12, width - 6);

  const args = message.args && Object.keys(message.args).length > 0 ? formatToolArgs(message.args) : '无参数';
  const output = message.output?.trim() ? message.output.trim() : '(无输出)';
  wrap(`args: ${args}`, availableWidth).forEach((line) => {
    lines.push(`${selected ? COLOR.selectedSubtle : COLOR.tool}${COLOR.dim}${UI_GLYPHS.toolDetailLeader}${line}${COLOR.reset}`);
  });
  wrap(`result: ${output}`, availableWidth).forEach((line) => {
    lines.push(`${selected ? COLOR.selectedSubtle : COLOR.tool}${COLOR.dim}${UI_GLYPHS.toolDetailLeader}${line}${COLOR.reset}`);
  });

  (message.subagents || []).forEach((subagent) => {
    const status = subagent.status === 'running' ? '执行中...' : '已完成';
    const summary = subagent.summary?.trim() ? ` · ${subagent.summary.trim()}` : '';
    wrap(
      `subagent ${subagent.subagent_type} · ${truncate(subagent.thread_id, 28)} · ${status}${summary}`,
      Math.max(12, width - 8),
    ).forEach((line) => {
      lines.push(`${selected ? COLOR.selectedSubtle : COLOR.tool}${UI_GLYPHS.subagentLeader}${line}${COLOR.reset}`);
    });
    subagent.tool_calls.forEach((toolCall) => {
      lines.push(...renderSubagentTool(toolCall, width));
    });
  });

  return lines;
}

function renderToolMessageLines(message: ToolMessage, width: number, selected: boolean): string[] {
  const bodyWidth = Math.max(12, width - 2);
  const summaryLines = getToolSummaryLines(message);
  const prefix = `${selected ? `${COLOR.selectedBorder}${COLOR.bold}` : COLOR.tool}${selected ? '▸' : '⏺'} ${COLOR.reset}`;
  const headline = wrapAnsiAware(formatToolSummary(message, bodyWidth), bodyWidth).map((line) =>
    styleToolRow(
      `${prefix}${selected ? `${COLOR.selectedText}${line}${COLOR.reset}` : `${COLOR.tool}${line}${COLOR.reset}`}`,
      width,
      selected,
    ),
  );

  const collapsedLines =
    !message.expanded && summaryLines.length > 0
      ? summaryLines.slice(0, 3).map((line) =>
          styleToolRow(
            `${selected ? `${COLOR.selectedBorder}${COLOR.bold}` : COLOR.tool}  ${COLOR.reset}${selected ? `${COLOR.selectedSubtle}${truncate(line, bodyWidth - 2)}${COLOR.reset}` : `${COLOR.secondary}${truncate(line, bodyWidth - 2)}${COLOR.reset}`}`,
            width,
            selected,
          ),
        )
      : [];

  return [...headline, ...(message.expanded ? renderToolDetails(message, width, selected) : collapsedLines)];
}

export function renderMessageLines(message: Message, width: number, selected = false): string[] {
  if (message.kind === 'message') {
    return renderTextMessageLines(message, width);
  }
  return renderToolMessageLines(message, width, selected);
}
