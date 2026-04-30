import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { useCallback, useEffect, useRef, type MutableRefObject } from 'react';
import { AnsiTextStream, sanitizeAnsiText } from '../ansiStream.js';
import { useAppState, type Message, type TextMessage, type ToolMessage } from './useAppState.js';
import type {
  BackendEvent,
  HistoryEntry,
  StatusPayload,
  SubagentRun,
  SubagentToolCall,
} from '../types/events.js';

type HistoryTextEntry = Extract<HistoryEntry, { role: string }>;

const SOURCE_ROOT = (() => {
  const configured = (process.env.NOCODE_SOURCE_ROOT || '').trim();
  if (configured) {
    return path.resolve(process.cwd(), expandUserPath(configured));
  }
  return path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
})();
const BACKEND_STDERR_CHAR_LIMIT = 4000;
const BACKEND_STDERR_LINE_LIMIT = 12;

export interface BackendConfig {
  resume?: boolean;
  model?: string;
}

function nextMessageId(prefix: string, counterRef: MutableRefObject<number>): string {
  const current = counterRef.current;
  counterRef.current += 1;
  return `${prefix}-${current}`;
}

function coerceRole(role?: string): 'user' | 'assistant' | 'system' {
  if (role === 'user' || role === 'assistant' || role === 'system') {
    return role;
  }
  return 'system';
}

function expandUserPath(rawPath: string): string {
  if (rawPath === '~') {
    return os.homedir();
  }
  if (rawPath.startsWith('~/')) {
    return path.join(os.homedir(), rawPath.slice(2));
  }
  return rawPath;
}

function resolveStateDir(projectDir: string): string {
  const configured = (process.env.NOCODE_STATE_DIR || '').trim();
  if (configured) {
    return path.resolve(process.cwd(), expandUserPath(configured));
  }

  let resolvedProjectDir = path.resolve(projectDir);
  try {
    resolvedProjectDir = fs.realpathSync(projectDir);
  } catch {
    // Fall back to resolved path when project dir does not exist yet.
  }

  const projectId = createHash('sha256').update(resolvedProjectDir).digest('hex').slice(0, 8);
  return path.join(os.homedir(), '.nocode', 'projects', projectId);
}

function resolveBackendLogPath(projectDir: string): string {
  const configured = (process.env.NOCODE_LOG_FILE || '').trim();
  if (!configured) {
    return path.join(resolveStateDir(projectDir), 'nocode.log');
  }

  const expanded = expandUserPath(configured);
  return path.isAbsolute(expanded) ? expanded : path.resolve(process.cwd(), expanded);
}

function getBackendStderrExcerpt(stderrTail: string): string {
  const text = stderrTail.trim();
  if (!text) {
    return '';
  }
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.length > 0);
  if (lines.length === 0) {
    return '';
  }
  return lines.slice(-BACKEND_STDERR_LINE_LIMIT).join('\n');
}

function buildBackendFailureMessage(baseMessage: string, stderrTail: string, logPath: string): string {
  const parts = [baseMessage];
  const stderrExcerpt = getBackendStderrExcerpt(stderrTail);
  if (stderrExcerpt) {
    parts.push(`最近 stderr:\n${stderrExcerpt}`);
  }
  if (logPath) {
    parts.push(`日志文件: ${logPath}`);
  }
  return parts.join('\n\n');
}

export function useBackend(config: BackendConfig = {}) {
  const backendRef = useRef<ChildProcessWithoutNullStreams | null>(null);
  const bufferRef = useRef('');
  const stderrTailRef = useRef('');
  const backendLogPathRef = useRef(resolveBackendLogPath(process.cwd()));
  const backendReportedFatalRef = useRef(false);
  const ansiStreamRef = useRef(new AnsiTextStream());
  const messageCounterRef = useRef(1);
  const subagentToolCounterRef = useRef(1);

  const addMessage = useAppState((state) => state.addMessage);
  const clearStreaming = useAppState((state) => state.clearStreaming);
  const permissionPreference = useAppState((state) => state.permissionPreference);
  const setGenerating = useAppState((state) => state.setGenerating);
  const setMessages = useAppState((state) => state.setMessages);
  const setPermissionRequest = useAppState((state) => state.setPermissionRequest);
  const setQuestionRequest = useAppState((state) => state.setQuestionRequest);
  const setSelectedToolId = useAppState((state) => state.setSelectedToolId);
  const setStatus = useAppState((state) => state.setStatus);
  const setStreaming = useAppState((state) => state.setStreaming);
  const setTranscriptScroll = useAppState((state) => state.setTranscriptScroll);
  const openModelPicker = useAppState((state) => state.openModelPicker);
  const openModelPickerFromCache = useAppState((state) => state.openModelPickerFromCache);
  const updateProviderFetch = useAppState((state) => state.updateProviderFetch);
  const setModelFetchLoading = useAppState((state) => state.setModelFetchLoading);
  const resetProviderFetchResults = useAppState((state) => state.resetProviderFetchResults);
  const openThreadPicker = useAppState((state) => state.openThreadPicker);
  const resetConversation = useAppState((state) => state.resetConversation);

  const pushSystemMessage = useCallback(
    (content: string) => {
      addMessage({
        id: nextMessageId('system', messageCounterRef),
        kind: 'message',
        role: 'system',
        content,
        timestamp: Date.now(),
      });
    },
    [addMessage],
  );

  const applyStatusPayload = useCallback(
    (payload: StatusPayload) => {
      setStatus({
        threadId: payload.thread_id,
        model: payload.model,
        modelName: payload.model_name || '',
        subagentModel: payload.subagent_model,
        reasoningEffort: payload.reasoning_effort,
        cwd: payload.cwd,
        contextWindow: payload.context_window,
        estimatedTokens: payload.estimated_tokens || 0,
        tokensLeftPercent: payload.tokens_left_percent,
      });
    },
    [setStatus],
  );

  const finalizeStreaming = useCallback(() => {
    const state = useAppState.getState();
    if (state.streaming) {
      addMessage({
        id: nextMessageId('assistant', messageCounterRef),
        kind: 'message',
        role: 'assistant',
        content: state.streaming,
        timestamp: Date.now(),
      });
    }
    clearStreaming();
    ansiStreamRef.current.reset();
    setGenerating(false);
  }, [addMessage, clearStreaming, setGenerating]);

  const findToolMessage = useCallback((toolCallId?: string): ToolMessage | undefined => {
    if (!toolCallId) {
      return undefined;
    }
    const { messages } = useAppState.getState();
    return [...messages]
      .reverse()
      .find((message): message is ToolMessage => message.kind === 'tool' && message.toolCallId === toolCallId);
  }, []);

  const ensureSubagentRun = useCallback(
    (
      parentToolCallId: string,
      subagentId: string,
      subagentType: string,
      threadId: string,
    ): SubagentRun | null => {
      const parent = findToolMessage(parentToolCallId);
      if (!parent) {
        return null;
      }

      let targetRun = parent.subagents?.find((run) => run.id === subagentId) || null;
      if (!targetRun) {
        targetRun = {
          id: subagentId,
          subagent_type: subagentType,
          thread_id: threadId,
          status: 'running',
          tool_calls: [],
        };
        useAppState.setState((state) => ({
          messages: state.messages.map((message) =>
            message.kind === 'tool' && message.id === parent.id
              ? {
                  ...message,
                  subagents: [...(message.subagents || []), targetRun!],
                }
              : message,
          ),
        }));
      }
      return targetRun;
    },
    [findToolMessage],
  );

  const handleHistory = useCallback(
    (entries: HistoryEntry[]) => {
      const messages: Message[] = entries.map((entry) => {
        if ('kind' in entry && entry.kind === 'tool') {
          return {
            id: nextMessageId('tool', messageCounterRef),
            kind: 'tool',
            name: entry.name,
            args: entry.args,
            output: entry.output,
            status: entry.status || 'done',
            expanded: false,
            toolCallId: entry.tool_call_id,
            subagents: entry.subagent_runs,
            timestamp: Date.now(),
          };
        }

        const textEntry = entry as HistoryTextEntry;

        return {
          id: nextMessageId('msg', messageCounterRef),
          kind: 'message',
          role: coerceRole(textEntry.role),
          content: sanitizeAnsiText(textEntry.content),
          timestamp: Date.now(),
        };
      });

      setMessages(messages);
      setSelectedToolId(null);
      setTranscriptScroll(0);
      clearStreaming();
      ansiStreamRef.current.reset();
      setGenerating(false);
    },
    [clearStreaming, setGenerating, setMessages, setSelectedToolId, setTranscriptScroll],
  );

  const handleEvent = useCallback(
    (event: BackendEvent) => {
      switch (event.type) {
        case 'hello':
          applyStatusPayload(event);
          if (config.resume) {
            backendRef.current?.stdin.write(JSON.stringify({ type: 'list_threads', source: 'tui' }) + '\n');
          }
          break;
        case 'status':
          applyStatusPayload(event);
          break;
        case 'resumed':
          applyStatusPayload(event);
          resetConversation();
          backendRef.current?.stdin.write(JSON.stringify({ type: 'load_history' }) + '\n');
          break;
        case 'cleared':
          resetConversation();
          ansiStreamRef.current.reset();
          setStatus({ threadId: event.thread_id });
          break;
        case 'text':
          setTranscriptScroll((value) => (value === 0 ? 0 : value));
          setStreaming((previous) => previous + ansiStreamRef.current.push(event.delta));
          break;
        case 'retry':
          pushSystemMessage(`Retry ${event.attempt}/${event.max_retries}: ${event.message}`);
          break;
        case 'tool_start': {
          // Flush any accumulated streaming text into a real message before adding the tool,
          // so that assistant text appears above tool calls in chronological order.
          const currentStreaming = useAppState.getState().streaming;
          if (currentStreaming) {
            addMessage({
              id: nextMessageId('assistant', messageCounterRef),
              kind: 'message',
              role: 'assistant',
              content: currentStreaming,
              timestamp: Date.now(),
            });
            clearStreaming();
            ansiStreamRef.current.reset();
          }
          const tool: ToolMessage = {
            id: nextMessageId('tool', messageCounterRef),
            kind: 'tool',
            name: event.name,
            args: event.args,
            status: 'running',
            expanded: false,
            toolCallId: event.tool_call_id,
            timestamp: Date.now(),
          };
          addMessage(tool);
          setTranscriptScroll(0);
          break;
        }
        case 'tool_end':
          useAppState.setState((state) => ({
            messages: state.messages.map((message) =>
              message.kind === 'tool' && message.toolCallId === event.tool_call_id
                ? { ...message, status: 'done', output: event.output }
                : message,
            ),
          }));
          break;
        case 'subagent_start':
          ensureSubagentRun(
            event.parent_tool_call_id,
            event.subagent_id,
            event.subagent_type,
            event.thread_id,
          );
          break;
        case 'subagent_tool_start': {
          const run = ensureSubagentRun(
            event.parent_tool_call_id,
            event.subagent_id,
            event.subagent_type,
            event.subagent_id,
          );
          if (!run) {
            break;
          }
          const toolCall: SubagentToolCall = {
            id: subagentToolCounterRef.current,
            name: event.name,
            args: event.args,
            status: 'running',
            tool_call_id: event.tool_call_id,
          };
          subagentToolCounterRef.current += 1;
          useAppState.setState((state) => ({
            messages: state.messages.map((message) =>
              message.kind === 'tool' && message.toolCallId === event.parent_tool_call_id
                ? {
                    ...message,
                    subagents: (message.subagents || []).map((subagent) =>
                      subagent.id === event.subagent_id
                        ? { ...subagent, tool_calls: [...subagent.tool_calls, toolCall] }
                        : subagent,
                    ),
                  }
                : message,
            ),
          }));
          break;
        }
        case 'subagent_tool_end':
          useAppState.setState((state) => ({
            messages: state.messages.map((message) =>
              message.kind === 'tool' && message.toolCallId === event.parent_tool_call_id
                ? {
                    ...message,
                    subagents: (message.subagents || []).map((subagent) =>
                      subagent.id === event.subagent_id
                        ? {
                            ...subagent,
                            tool_calls: subagent.tool_calls.map((toolCall) =>
                              toolCall.tool_call_id === event.tool_call_id
                                ? { ...toolCall, status: 'done', output: event.output }
                                : toolCall,
                            ),
                          }
                        : subagent,
                    ),
                  }
                : message,
            ),
          }));
          break;
        case 'subagent_finish':
          useAppState.setState((state) => ({
            messages: state.messages.map((message) =>
              message.kind === 'tool' && message.toolCallId === event.parent_tool_call_id
                ? {
                    ...message,
                    subagents: (message.subagents || []).map((subagent) =>
                      subagent.id === event.subagent_id
                        ? { ...subagent, status: 'done', summary: event.summary }
                        : subagent,
                    ),
                  }
                : message,
            ),
          }));
          break;
        case 'question':
          setQuestionRequest({
            toolCallId: event.tool_call_id,
            questions: event.questions,
            questionIndex: 0,
            optionIndex: 0,
            selectedOptions: [],
            textAnswer: '',
            answers: [],
          });
          break;
        case 'permission_request': {
          if (permissionPreference === 'all' && event.actions.length > 0) {
            backendRef.current?.stdin.write(
              JSON.stringify({
                type: 'permission_decision',
                request_id: event.request_id,
                decisions: event.actions.map(() => ({ type: 'approve' })),
              }) + '\n',
            );
            pushSystemMessage(`Auto-approved ${event.actions.length} tool permission request(s).`);
            break;
          }

          setPermissionRequest({
            requestId: event.request_id,
            actions: event.actions,
            actionIndex: 0,
            optionIndex: 0,
            decisions: [],
            parentToolCallId: event.parent_tool_call_id,
            subagentId: event.subagent_id,
            subagentType: event.subagent_type,
          });
          break;
        }
        case 'done':
          finalizeStreaming();
          break;
        case 'error':
          pushSystemMessage(`Error: ${event.message}`);
          finalizeStreaming();
          break;
        case 'fatal': {
          backendReportedFatalRef.current = true;
          pushSystemMessage(
            buildBackendFailureMessage(
              `fatal: ${event.message}`,
              stderrTailRef.current,
              backendLogPathRef.current,
            ),
          );
          finalizeStreaming();
          break;
        }
        case 'cancelled':
          finalizeStreaming();
          break;
        case 'auto_compact_start':
          pushSystemMessage('Auto compact started.');
          break;
        case 'auto_compact_done':
          pushSystemMessage(
            `Auto compact done: ${event.strategy}, ${event.pre_tokens} -> ${event.post_tokens}, restored ${event.files_restored} file(s).`,
          );
          break;
        case 'auto_compact_failed':
          pushSystemMessage('Auto compact failed.');
          break;
        case 'token_usage':
          setStatus({
            contextWindow: event.context_window,
            tokensLeftPercent: event.tokens_left_percent,
          });
          break;
        case 'prompt_queued':
          addMessage({
            id: nextMessageId('queued', messageCounterRef),
            kind: 'message',
            role: 'user',
            content: event.text,
            state: 'queued',
            timestamp: Date.now(),
          } satisfies TextMessage);
          setTranscriptScroll(0);
          break;
        case 'queued_prompt_injected':
          useAppState.setState((state) => {
            const pending = [...event.texts];
            return {
              messages: state.messages.map((message) => {
                if (
                  message.kind === 'message' &&
                  message.role === 'user' &&
                  message.state === 'queued'
                ) {
                  const index = pending.indexOf(message.content);
                  if (index >= 0) {
                    pending.splice(index, 1);
                    return { ...message, state: 'sent' };
                  }
                }
                return message;
              }),
            };
          });
          break;
        case 'thread_list':
          openThreadPicker(event.threads);
          break;
        case 'history':
          handleHistory(event.messages);
          break;
        case 'models_fetch_start':
          setModelFetchLoading(true);
          resetProviderFetchResults(event.providers);
          break;
        case 'models_fetch_provider':
          updateProviderFetch(event.result);
          break;
        case 'models_fetch_done':
          setModelFetchLoading(false);
          openModelPickerFromCache(event.cache, event.current, event.default, useAppState.getState().providerFetchResults);
          break;
        case 'model_switched':
          setStatus({ modelName: event.model_name, model: event.model });
          pushSystemMessage(`Switched to model ${event.model_name} (${event.model}).`);
          break;
        default:
          break;
      }
    },
    [
      addMessage,
      applyStatusPayload,
      config.resume,
      ensureSubagentRun,
      finalizeStreaming,
      handleHistory,
      openModelPicker,
      openModelPickerFromCache,
      openThreadPicker,
      updateProviderFetch,
      setModelFetchLoading,
      resetProviderFetchResults,
      permissionPreference,
      pushSystemMessage,
      resetConversation,
      setGenerating,
      setPermissionRequest,
      setQuestionRequest,
      setSelectedToolId,
      setStatus,
      setStreaming,
    ],
  );

  useEffect(() => {
    const baseEnv = { ...process.env };
    delete baseEnv.NOCODE_PROJECT_DIR;
    backendLogPathRef.current = resolveBackendLogPath(process.cwd());
    backendReportedFatalRef.current = false;

    const localPython =
      process.platform === 'win32'
        ? path.join(SOURCE_ROOT, '.venv', 'Scripts', 'python.exe')
        : path.join(SOURCE_ROOT, '.venv', 'bin', 'python');
    const pythonBin = fs.existsSync(localPython)
      ? localPython
      : process.env.PYTHON_BIN || (process.platform === 'win32' ? 'python' : 'python3');
    const pythonPathEntries = [path.join(SOURCE_ROOT, 'src')];
    if (process.env.PYTHONPATH) {
      pythonPathEntries.push(process.env.PYTHONPATH);
    }

    const backend = spawn(pythonBin, ['-m', 'nocode_agent.app.backend_stdio'], {
      cwd: process.cwd(),
      env: {
        ...baseEnv,
        ...(config.model ? { NOCODE_MODEL_NAME: config.model } : {}),
        PYTHONPATH: pythonPathEntries.join(path.delimiter),
      },
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    backendRef.current = backend;
    backend.stdout.setEncoding('utf8');
    backend.stderr.setEncoding('utf8');

    backend.stdout.on('data', (chunk: string) => {
      bufferRef.current += chunk;
      let newlineIndex = bufferRef.current.indexOf('\n');
      while (newlineIndex >= 0) {
        const line = bufferRef.current.slice(0, newlineIndex).trim();
        bufferRef.current = bufferRef.current.slice(newlineIndex + 1);
        if (line) {
          try {
            handleEvent(JSON.parse(line) as BackendEvent);
          } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            pushSystemMessage(`Invalid backend event: ${message}\n${line}`);
          }
        }
        newlineIndex = bufferRef.current.indexOf('\n');
      }
    });

    backend.stderr.on('data', (chunk: string) => {
      stderrTailRef.current = `${stderrTailRef.current}${chunk}`.slice(-BACKEND_STDERR_CHAR_LIMIT);
    });

    backend.on('close', (code) => {
      if (backendReportedFatalRef.current || code === null || code === 0) {
        return;
      }
      pushSystemMessage(
        buildBackendFailureMessage(
          `backend exited with code ${code}`,
          stderrTailRef.current,
          backendLogPathRef.current,
        ),
      );
    });

    return () => {
      backend.kill();
      backendRef.current = null;
    };
  }, [handleEvent, pushSystemMessage]);

  const send = useCallback((payload: Record<string, unknown>) => {
    backendRef.current?.stdin.write(`${JSON.stringify(payload)}\n`);
  }, []);

  const sendPrompt = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) {
        return;
      }

      addMessage({
        id: nextMessageId('user', messageCounterRef),
        kind: 'message',
        role: 'user',
        content: trimmed,
        state: 'sent',
        timestamp: Date.now(),
      });
      setGenerating(true);
      setTranscriptScroll(0);
      send({ type: 'prompt', text: trimmed });
    },
    [addMessage, send, setGenerating, setTranscriptScroll],
  );

  const sendQuestionAnswer = useCallback(
    (text: string) => {
      send({ type: 'question_answer', text });
    },
    [send],
  );

  const sendPermissionDecisions = useCallback(
    (requestId: string, decisions: Array<{ type: 'approve' | 'reject'; message?: string }>) => {
      send({ type: 'permission_decision', request_id: requestId, decisions });
    },
    [send],
  );

  const fetchModels = useCallback(() => {
    send({ type: 'fetch_models' });
  }, [send]);

  const refreshModels = useCallback(() => {
    send({ type: 'fetch_models', force: true });
  }, [send]);

  const switchModel = useCallback(
    (model: string) => {
      send({ type: 'switch_model', model });
    },
    [send],
  );

  const listThreads = useCallback(() => {
    send({ type: 'list_threads', source: 'tui' });
  }, [send]);

  const resumeThread = useCallback(
    (threadId: string) => {
      send({ type: 'resume_thread', thread_id: threadId });
    },
    [send],
  );

  const loadHistory = useCallback(() => {
    send({ type: 'load_history' });
  }, [send]);

  const clearConversation = useCallback(() => {
    send({ type: 'clear' });
  }, [send]);

  const requestStatus = useCallback(() => {
    send({ type: 'status' });
  }, [send]);

  const cancel = useCallback(() => {
    send({ type: 'cancel' });
  }, [send]);

  return {
    sendPrompt,
    sendQuestionAnswer,
    sendPermissionDecisions,
    fetchModels,
    refreshModels,
    switchModel,
    listThreads,
    resumeThread,
    loadHistory,
    clearConversation,
    requestStatus,
    cancel,
  };
}
