import { create } from 'zustand';
import type {
  PermissionAction,
  Question,
  SubagentRun,
  ThreadInfo,
} from '../types/events.js';

export type Role = 'user' | 'assistant' | 'system';

export interface TextMessage {
  id: string;
  kind: 'message';
  role: Role;
  content: string;
  state?: 'queued' | 'sent';
  timestamp: number;
}

export interface ToolMessage {
  id: string;
  kind: 'tool';
  name: string;
  args?: Record<string, unknown>;
  output?: string;
  status: 'running' | 'done';
  expanded: boolean;
  toolCallId?: string;
  subagents?: SubagentRun[];
  timestamp: number;
}

export type Message = TextMessage | ToolMessage;

export interface ModelOption {
  name: string;
  model: string;
  is_default: string;
}

export interface PermissionRequestState {
  requestId: string;
  actions: PermissionAction[];
  actionIndex: number;
  optionIndex: number;
  decisions: Array<{ type: 'approve' | 'reject'; message?: string }>;
  parentToolCallId?: string;
  subagentId?: string;
  subagentType?: string;
}

export interface QuestionRequestState {
  toolCallId: string;
  questions: Question[];
  questionIndex: number;
  optionIndex: number;
  selectedOptions: string[];
  textAnswer: string;
  answers: string[];
}

export interface AppState {
  messages: Message[];
  streaming: string;
  generating: boolean;
  generatingStartedAt: number;
  model: string;
  modelName: string;
  subagentModel: string;
  threadId: string;
  cwd: string;
  reasoningEffort: string;
  contextWindow: number;
  estimatedTokens: number;
  tokensLeftPercent: number;
  transcriptScroll: number;
  selectedToolId: string | null;
  permissionPreference: 'ask' | 'all';
  modelOptions: ModelOption[];
  modelPickerOpen: boolean;
  modelPickerIndex: number;
  threads: ThreadInfo[];
  threadPickerOpen: boolean;
  threadPickerIndex: number;
  permissionRequest: PermissionRequestState | null;
  questionRequest: QuestionRequestState | null;
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  updateMessage: (id: string, updater: (message: Message) => Message) => void;
  setStreaming: (value: string | ((prev: string) => string)) => void;
  clearStreaming: () => void;
  setGenerating: (value: boolean) => void;
  setStatus: (payload: Partial<Pick<AppState, 'model' | 'modelName' | 'subagentModel' | 'threadId' | 'cwd' | 'reasoningEffort' | 'contextWindow' | 'estimatedTokens' | 'tokensLeftPercent'>>) => void;
  setTranscriptScroll: (value: number | ((prev: number) => number)) => void;
  setSelectedToolId: (id: string | null) => void;
  toggleToolExpanded: (id: string) => void;
  setPermissionPreference: (mode: 'ask' | 'all') => void;
  openModelPicker: (models: ModelOption[], selectedName?: string) => void;
  closeModelPicker: () => void;
  moveModelPicker: (delta: number) => void;
  openThreadPicker: (threads: ThreadInfo[]) => void;
  closeThreadPicker: () => void;
  moveThreadPicker: (delta: number) => void;
  setPermissionRequest: (request: PermissionRequestState | null) => void;
  updatePermissionRequest: (updater: (request: PermissionRequestState) => PermissionRequestState | null) => void;
  setQuestionRequest: (request: QuestionRequestState | null) => void;
  updateQuestionRequest: (updater: (request: QuestionRequestState) => QuestionRequestState | null) => void;
  resetConversation: () => void;
}

export const useAppState = create<AppState>((set) => ({
  messages: [],
  streaming: '',
  generating: false,
  generatingStartedAt: 0,
  model: '',
  modelName: '',
  subagentModel: '',
  threadId: '',
  cwd: '',
  reasoningEffort: '',
  contextWindow: 128000,
  estimatedTokens: 0,
  tokensLeftPercent: 100,
  transcriptScroll: 0,
  selectedToolId: null,
  permissionPreference: 'ask',
  modelOptions: [],
  modelPickerOpen: false,
  modelPickerIndex: 0,
  threads: [],
  threadPickerOpen: false,
  threadPickerIndex: 0,
  permissionRequest: null,
  questionRequest: null,
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setMessages: (messages) => set({ messages }),
  updateMessage: (id, updater) =>
    set((state) => ({
      messages: state.messages.map((message) => (message.id === id ? updater(message) : message)),
    })),
  setStreaming: (value) =>
    set((state) => ({
      streaming: typeof value === 'function' ? value(state.streaming) : value,
    })),
  clearStreaming: () => set({ streaming: '' }),
  setGenerating: (value) =>
    set((state) => ({
      generating: value,
      generatingStartedAt: value ? state.generatingStartedAt || Date.now() : 0,
    })),
  setStatus: (payload) => set(payload),
  setTranscriptScroll: (value) =>
    set((state) => ({
      transcriptScroll: typeof value === 'function' ? value(state.transcriptScroll) : value,
    })),
  setSelectedToolId: (id) => set({ selectedToolId: id }),
  toggleToolExpanded: (id) =>
    set((state) => ({
      messages: state.messages.map((message) =>
        message.kind === 'tool' && message.id === id
          ? { ...message, expanded: !message.expanded }
          : message,
      ),
    })),
  setPermissionPreference: (mode) => set({ permissionPreference: mode }),
  openModelPicker: (models, selectedName) =>
    set(() => {
      const index = selectedName ? Math.max(0, models.findIndex((model) => model.name === selectedName)) : 0;
      return {
        modelOptions: models,
        modelPickerOpen: true,
        modelPickerIndex: index,
      };
    }),
  closeModelPicker: () => set({ modelPickerOpen: false, modelOptions: [], modelPickerIndex: 0 }),
  moveModelPicker: (delta) =>
    set((state) => ({
      modelPickerIndex:
        state.modelOptions.length === 0
          ? 0
          : Math.max(0, Math.min(state.modelOptions.length - 1, state.modelPickerIndex + delta)),
    })),
  openThreadPicker: (threads) => set({ threads, threadPickerOpen: true, threadPickerIndex: 0 }),
  closeThreadPicker: () => set({ threadPickerOpen: false, threads: [], threadPickerIndex: 0 }),
  moveThreadPicker: (delta) =>
    set((state) => ({
      threadPickerIndex:
        state.threads.length === 0
          ? 0
          : Math.max(0, Math.min(state.threads.length - 1, state.threadPickerIndex + delta)),
    })),
  setPermissionRequest: (request) => set({ permissionRequest: request }),
  updatePermissionRequest: (updater) =>
    set((state) => ({
      permissionRequest: state.permissionRequest ? updater(state.permissionRequest) : null,
    })),
  setQuestionRequest: (request) => set({ questionRequest: request }),
  updateQuestionRequest: (updater) =>
    set((state) => ({
      questionRequest: state.questionRequest ? updater(state.questionRequest) : null,
    })),
  resetConversation: () =>
    set({
      messages: [],
      streaming: '',
      generating: false,
      generatingStartedAt: 0,
      transcriptScroll: 0,
      selectedToolId: null,
      permissionRequest: null,
      questionRequest: null,
    }),
}));
