import { create } from 'zustand';

export interface Message {
  id: string;
  kind: 'user' | 'assistant' | 'system' | 'tool' | 'subagent' | 'message';
  role?: string;
  content?: string;
  name?: string;
  status?: 'queued' | 'running' | 'done' | 'error';
  output?: string;
  args?: Record<string, unknown>;
  tool_call_id?: string;
  subagent_type?: string;
  thread_id?: string;
  timestamp: number;
}

export interface AppState {
  // 状态
  messages: Message[];
  streaming: string;
  generating: boolean;
  model: string;
  modelName: string;
  threadId: string;
  cwd: string;
  reasoningEffort: string;
  
  // 工具选择
  selectedToolId: string | null;
  toolQueue: Array<{ name: string; args: Record<string, unknown>; tool_call_id: string }>;
  
  // UI 状态
  showModelPicker: boolean;
  showPermissionPicker: boolean;
  permissionMode: boolean;
  
  // 方法
  addMessage: (msg: Message) => void;
  setStreaming: (text: string | ((prev: string) => string)) => void;
  setGenerating: (bool: boolean) => void;
  setModel: (model: string, modelName: string) => void;
  setCwd: (cwd: string) => void;
  setThreadId: (id: string) => void;
  setShowModelPicker: (show: boolean) => void;
  clearStreaming: () => void;
}

export const useAppState = create<AppState>((set, get) => ({
  // 初始状态
  messages: [],
  streaming: '',
  generating: false,
  model: '',
  modelName: '',
  threadId: '',
  cwd: '',
  reasoningEffort: '',
  selectedToolId: null,
  toolQueue: [],
  showModelPicker: false,
  showPermissionPicker: false,
  permissionMode: false,
  
  // 方法
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  
  setStreaming: (text) => set((state) => ({
    streaming: typeof text === 'function' ? text(state.streaming) : text
  })),
  
  setGenerating: (bool) => set({ generating: bool }),
  
  setModel: (model, modelName) => set({ model, modelName }),
  
  setCwd: (cwd) => set({ cwd }),
  
  setThreadId: (id) => set({ threadId: id }),
  
  setShowModelPicker: (show) => set({ showModelPicker: show }),
  
  clearStreaming: () => set({ streaming: '' }),
}));