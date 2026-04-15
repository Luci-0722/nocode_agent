export type Role = 'user' | 'assistant' | 'system';

export interface StatusPayload {
  thread_id: string;
  model: string;
  model_name?: string;
  subagent_model: string;
  reasoning_effort: string;
  cwd: string;
  context_window: number;
  estimated_tokens?: number;
  tokens_left_percent: number;
}

export interface QuestionOption {
  label: string;
  description?: string;
}

export interface Question {
  question: string;
  header?: string;
  options?: QuestionOption[];
  multiSelect?: boolean;
}

export interface PermissionAction {
  name: string;
  args?: Record<string, unknown>;
  description?: string;
  allowed_decisions: Array<'approve' | 'reject'>;
  tool_call_id?: string;
}

export interface ThreadInfo {
  thread_id: string;
  preview: string;
  message_count: number;
  source?: string;
}

export type AutoCompactStrategy = 'session_memory' | 'summary';

export interface SubagentToolCall {
  id: number;
  name: string;
  args?: Record<string, unknown>;
  output?: string;
  status: 'running' | 'done';
  tool_call_id?: string;
}

export interface SubagentRun {
  id: string;
  subagent_type: string;
  thread_id: string;
  status: 'running' | 'done';
  summary?: string;
  tool_calls: SubagentToolCall[];
}

export type HistoryEntry =
  | { role: string; content: string }
  | {
      kind: 'tool';
      name: string;
      args?: Record<string, unknown>;
      output?: string;
      status?: 'running' | 'done';
      tool_call_id?: string;
      subagent_runs?: SubagentRun[];
    };

export type BackendEvent =
  | ({ type: 'hello' } & StatusPayload)
  | ({ type: 'status' } & StatusPayload)
  | ({ type: 'resumed' } & StatusPayload)
  | { type: 'cleared'; thread_id: string }
  | { type: 'text'; delta: string }
  | { type: 'retry'; message: string; attempt: number; max_retries: number; delay: number }
  | { type: 'tool_start'; name: string; args?: Record<string, unknown>; tool_call_id?: string }
  | { type: 'tool_end'; name: string; output?: string; tool_call_id?: string }
  | {
      type: 'subagent_start';
      parent_tool_call_id: string;
      subagent_id: string;
      subagent_type: string;
      thread_id: string;
    }
  | {
      type: 'subagent_tool_start';
      parent_tool_call_id: string;
      subagent_id: string;
      subagent_type: string;
      name: string;
      args?: Record<string, unknown>;
      tool_call_id?: string;
    }
  | {
      type: 'subagent_tool_end';
      parent_tool_call_id: string;
      subagent_id: string;
      subagent_type: string;
      name: string;
      output?: string;
      tool_call_id?: string;
    }
  | {
      type: 'subagent_finish';
      parent_tool_call_id: string;
      subagent_id: string;
      subagent_type: string;
      summary?: string;
    }
  | { type: 'question'; questions: Question[]; tool_call_id: string }
  | {
      type: 'permission_request';
      request_id: string;
      actions: PermissionAction[];
      parent_tool_call_id?: string;
      subagent_id?: string;
      subagent_type?: string;
    }
  | { type: 'done' }
  | { type: 'error'; message: string }
  | { type: 'fatal'; message: string }
  | { type: 'cancelled' }
  | { type: 'auto_compact_start' }
  | {
      type: 'auto_compact_done';
      strategy: AutoCompactStrategy;
      pre_tokens: number;
      post_tokens: number;
      files_restored: number;
    }
  | { type: 'auto_compact_failed' }
  | { type: 'token_usage'; input_tokens: number; context_window: number; tokens_left: number; tokens_left_percent: number }
  | { type: 'prompt_queued'; text: string }
  | { type: 'queued_prompt_injected'; texts: string[] }
  | { type: 'thread_list'; threads: ThreadInfo[] }
  | { type: 'history'; messages: HistoryEntry[] }
  | { type: 'model_list'; models: { name: string; model: string; is_default: string }[]; current: string; default: string }
  | { type: 'model_switched'; model_name: string; model: string };
