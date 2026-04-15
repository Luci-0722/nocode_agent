// 后端事件类型定义

export type Role = "user" | "assistant" | "system";

export interface StatusPayload {
  thread_id: string;
  model: string;
  model_name: string;
  cwd: string;
  reasoning_effort?: string;
  context_window: number;
  estimated_tokens: number;
  tokens_left_percent: number;
}

export interface Question {
  question: string;
  header?: string;
  options?: Array<{ label: string; description?: string }>;
  multi_select?: boolean;
}

export interface PermissionAction {
  tool_name: string;
  args?: Record<string, unknown>;
  risk?: string;
  read_only?: boolean;
}

export interface ThreadInfo {
  thread_id: string;
  created_at: string;
  last_message?: string;
}

export type AutoCompactStrategy = "truncation" | "session_memory" | "hybrid";

export type BackendEvent =
  | ({ type: "hello" } & StatusPayload)
  | ({ type: "status" } & StatusPayload)
  | { type: "cleared"; thread_id: string }
  | { type: "text"; delta: string }
  | { type: "retry"; message: string; attempt: number; max_retries: number; delay: number }
  | { type: "tool_start"; name: string; args?: Record<string, unknown>; tool_call_id?: string }
  | { type: "tool_end"; name: string; output?: string; tool_call_id?: string }
  | {
      type: "subagent_start";
      parent_tool_call_id: string;
      subagent_id: string;
      subagent_type: string;
      thread_id: string;
    }
  | {
      type: "subagent_tool_start";
      parent_tool_call_id: string;
      subagent_id: string;
      subagent_type: string;
      name: string;
      args?: Record<string, unknown>;
      tool_call_id?: string;
    }
  | {
      type: "subagent_tool_end";
      parent_tool_call_id: string;
      subagent_id: string;
      subagent_type: string;
      name: string;
      output?: string;
      tool_call_id?: string;
    }
  | {
      type: "subagent_finish";
      parent_tool_call_id: string;
      subagent_id: string;
      subagent_type: string;
      summary?: string;
    }
  | { type: "question"; questions: Question[]; tool_call_id: string }
  | {
      type: "permission_request";
      request_id: string;
      actions: PermissionAction[];
      parent_tool_call_id?: string;
      subagent_id?: string;
      subagent_type?: string;
    }
  | { type: "done" }
  | { type: "error"; message: string }
  | { type: "fatal"; message: string }
  | { type: "cancelled" }
  | { type: "auto_compact_start" }
  | {
      type: "auto_compact_done";
      strategy: AutoCompactStrategy;
      pre_tokens: number;
      post_tokens: number;
      files_restored: number;
    }
  | { type: "auto_compact_failed" }
  | { type: "token_usage"; input_tokens: number; context_window: number; tokens_left: number; tokens_left_percent: number }
  | { type: "prompt_queued"; text: string }
  | { type: "queued_prompt_injected"; texts: string[] }
  | { type: "thread_list"; threads: ThreadInfo[] }
  | ({ type: "resumed" } & StatusPayload)
  | {
      type: "history";
      messages: Array<
        | { role: string; content: string }
        | {
            kind: "tool";
            name: string;
            args?: Record<string, unknown>;
            output?: string;
            status: "running" | "done";
            tool_call_id?: string;
            subagent_runs?: SubagentRun[];
          }
      >;
    }
  | { type: "model_switched"; model: string; model_name: string }
  | { type: "permission_decision"; request_id: string; decision: "allow" | "deny" };

export interface SubagentRun {
  id: string;
  subagent_type: string;
  thread_id: string;
  status: "running" | "done";
  summary?: string;
  tool_calls: SubagentToolCall[];
}

export interface SubagentToolCall {
  id: number;
  name: string;
  args?: Record<string, unknown>;
  output?: string;
  status: "running" | "done";
  tool_call_id?: string;
}