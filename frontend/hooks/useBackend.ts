import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { useCallback, useEffect, useRef, type MutableRefObject } from 'react';
import { useAppState, type Message, type TextMessage, type ToolMessage } from './useAppState.js';
import type {
  BackendEvent,
  HistoryEntry,
  StatusPayload,
  SubagentRun,
  SubagentToolCall,
} from '../types/events.js';

type HistoryTextEntry = Extract<HistoryEntry, { role: string }>;

const SOURCE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');

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

export function useBackend(config: BackendConfig = {}) {
  const backendRef = useRef<ChildProcessWithoutNullStreams | null>(null);
  const bufferRef = useRef('');
  const stderrTailRef = useRef('');
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
  const openModelPicker = useAppState((state) => state.openModelPicker);
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
          content: textEntry.content,
          timestamp: Date.now(),
        };
      });

      setMessages(messages);
      setSelectedToolId(null);
      clearStreaming();
      setGenerating(false);
    },
    [clearStreaming, setGenerating, setMessages, setSelectedToolId],
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
          setStatus({ threadId: event.thread_id });
          break;
        case 'text':
          setStreaming((previous) => previous + event.delta);
          break;
        case 'retry':
          pushSystemMessage(`Retry ${event.attempt}/${event.max_retries}: ${event.message}`);
          break;
        case 'tool_start': {
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
          setSelectedToolId(tool.id);
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
          const stderr = stderrTailRef.current.trim();
          const suffix = stderr ? `\n\nRecent stderr:\n${stderr}` : '';
          pushSystemMessage(`Fatal: ${event.message}${suffix}`);
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
        case 'model_list':
          openModelPicker(event.models, event.current);
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
      openThreadPicker,
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
      stderrTailRef.current = `${stderrTailRef.current}${chunk}`.slice(-4000);
    });

    backend.on('close', (code) => {
      if (code !== 0) {
        const stderr = stderrTailRef.current.trim();
        const suffix = stderr ? `\n\nRecent stderr:\n${stderr}` : '';
        pushSystemMessage(`Backend exited with code ${code}.${suffix}`);
      }
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
      send({ type: 'prompt', text: trimmed });
    },
    [addMessage, send, setGenerating],
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

  const listModels = useCallback(() => {
    send({ type: 'list_models' });
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
    listModels,
    switchModel,
    listThreads,
    resumeThread,
    loadHistory,
    clearConversation,
    requestStatus,
    cancel,
  };
}
