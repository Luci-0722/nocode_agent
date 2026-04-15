import { spawn, ChildProcessWithoutNullStreams } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { useEffect, useRef, useCallback } from 'react';
import { useAppState, Message } from './useAppState.js';
import type { BackendEvent, StatusPayload, SubagentRun, SubagentToolCall } from '../types/events.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export interface BackendConfig {
  resume?: boolean;
  model?: string;
}

export function useBackend(config: BackendConfig = {}) {
  const backendRef = useRef<ChildProcessWithoutNullStreams | null>(null);
  const messageIdRef = useRef(0);
  const toolIdRef = useRef(0);
  const subagentRunsRef = useRef<Map<string, SubagentRun>>(new Map());
  
  const {
    addMessage,
    setStreaming,
    setGenerating,
    setModel,
    setCwd,
    setThreadId,
  } = useAppState();
  
  // 启动后端进程
  useEffect(() => {
    const projectDir = findProjectDir();
    const venvPython = path.join(projectDir, '.venv', 'bin', 'python3');
    const pythonBin = fs.existsSync(venvPython) ? venvPython : 'python3';
    
    const args = ['-m', 'nocode_agent.app.backend_stdio'];
    if (config.resume) {
      args.push('--resume');
    }
    if (config.model) {
      args.push('--model', config.model);
    }
    
    const backend = spawn(pythonBin, args, {
      cwd: projectDir,
      env: {
        ...process.env,
        NOCODE_PROJECT_DIR: projectDir,
        PYTHONPATH: path.join(projectDir, 'src'),
      },
    });
    
    backendRef.current = backend;
    
    // 解析事件流
    let buffer = '';
    backend.stdout.on('data', (data: Buffer) => {
      buffer += data.toString();
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (line.trim()) {
          try {
            const event = JSON.parse(line) as BackendEvent;
            handleEvent(event);
          } catch (e) {
            console.error('Failed to parse event:', line, e);
          }
        }
      }
    });
    
    backend.stderr.on('data', (data: Buffer) => {
      console.error('[backend stderr]', data.toString());
    });
    
    backend.on('close', (code) => {
      console.error('[backend closed]', code);
    });
    
    return () => {
      backend.kill();
    };
  }, []);
  
  // 处理事件
  const handleEvent = (event: BackendEvent) => {
    switch (event.type) {
      case 'hello':
      case 'status':
      case 'resumed':
        applyStatusPayload(event);
        break;
        
      case 'text':
        setStreaming((prev) => prev + event.delta);
        break;
        
      case 'tool_start':
        handleToolStart(event);
        break;
        
      case 'tool_end':
        handleToolEnd(event);
        break;
        
      case 'subagent_start':
        handleSubagentStart(event);
        break;
        
      case 'subagent_tool_start':
      case 'subagent_tool_end':
        handleSubagentToolEvent(event);
        break;
        
      case 'subagent_finish':
        handleSubagentFinish(event);
        break;
        
      case 'done':
        finalizeStreaming();
        break;
        
      case 'error':
        addMessage({
          id: `msg-${messageIdRef.current++}`,
          kind: 'system',
          role: 'system',
          content: `Error: ${event.message}`,
          timestamp: Date.now(),
        });
        finalizeStreaming();
        break;
        
      case 'fatal':
        addMessage({
          id: `msg-${messageIdRef.current++}`,
          kind: 'system',
          role: 'system',
          content: `Fatal: ${event.message}`,
          timestamp: Date.now(),
        });
        finalizeStreaming();
        break;
        
      case 'cancelled':
        finalizeStreaming();
        break;
        
      case 'model_switched':
        setModel(event.model, event.model_name);
        break;
        
      case 'history':
        handleHistory(event.messages);
        break;
    }
  };
  
  const applyStatusPayload = (payload: StatusPayload) => {
    setThreadId(payload.thread_id);
    setModel(payload.model, payload.model_name);
    setCwd(payload.cwd);
  };
  
  const handleToolStart = (event: { name: string; args?: Record<string, unknown>; tool_call_id?: string }) => {
    addMessage({
      id: `tool-${toolIdRef.current++}`,
      kind: 'tool',
      name: event.name,
      args: event.args,
      status: 'running',
      tool_call_id: event.tool_call_id,
      timestamp: Date.now(),
    });
  };
  
  const handleToolEnd = (event: { name: string; output?: string; tool_call_id?: string }) => {
    // 更新工具状态
    useAppState.setState((state) => ({
      messages: state.messages.map((msg) =>
        msg.kind === 'tool' && msg.tool_call_id === event.tool_call_id
          ? { ...msg, status: 'done', output: event.output }
          : msg
      ),
    }));
  };
  
  const handleSubagentStart = (event: {
    parent_tool_call_id: string;
    subagent_id: string;
    subagent_type: string;
    thread_id: string;
  }) => {
    const run: SubagentRun = {
      id: event.subagent_id,
      subagent_type: event.subagent_type,
      thread_id: event.thread_id,
      status: 'running',
      tool_calls: [],
    };
    subagentRunsRef.current.set(event.subagent_id, run);
  };
  
  const handleSubagentToolEvent = (event: {
    type: 'subagent_tool_start' | 'subagent_tool_end';
    subagent_id: string;
    name: string;
    args?: Record<string, unknown>;
    output?: string;
    tool_call_id?: string;
  }) => {
    const run = subagentRunsRef.current.get(event.subagent_id);
    if (!run) return;
    
    if (event.type === 'subagent_tool_start') {
      run.tool_calls.push({
        id: toolIdRef.current++,
        name: event.name,
        args: event.args,
        status: 'running',
        tool_call_id: event.tool_call_id,
      });
    } else {
      const tc = run.tool_calls.find((t) => t.tool_call_id === event.tool_call_id);
      if (tc) {
        tc.status = 'done';
        tc.output = event.output;
      }
    }
  };
  
  const handleSubagentFinish = (event: { subagent_id: string; summary?: string }) => {
    const run = subagentRunsRef.current.get(event.subagent_id);
    if (run) {
      run.status = 'done';
      run.summary = event.summary;
    }
  };
  
  const handleHistory = (messages: BackendEvent extends { type: 'history' } ? never : any) => {
    // 转换历史消息
    const converted: Message[] = messages.map((msg: any) => {
      if (msg.kind === 'tool') {
        return {
          id: `tool-${toolIdRef.current++}`,
          kind: 'tool',
          name: msg.name,
          args: msg.args,
          output: msg.output,
          status: msg.status,
          tool_call_id: msg.tool_call_id,
          timestamp: Date.now(),
        };
      }
      return {
        id: `msg-${messageIdRef.current++}`,
        kind: 'message',
        role: msg.role,
        content: msg.content,
        timestamp: Date.now(),
      };
    });
    useAppState.setState({ messages: converted });
  };
  
  const finalizeStreaming = () => {
    const { streaming } = useAppState.getState();
    if (streaming) {
      addMessage({
        id: `msg-${messageIdRef.current++}`,
        kind: 'message',
        role: 'assistant',
        content: streaming,
        timestamp: Date.now(),
      });
    }
    setStreaming('');
    setGenerating(false);
  };
  
  // 发送提示词
  const sendPrompt = useCallback((text: string) => {
    if (!backendRef.current) return;
    
    addMessage({
      id: `msg-${messageIdRef.current++}`,
      kind: 'message',
      role: 'user',
      content: text,
      timestamp: Date.now(),
    });
    
    backendRef.current.stdin.write(JSON.stringify({ type: 'prompt', text }) + '\n');
    setGenerating(true);
  }, [addMessage, setGenerating]);
  
  // 发送权限决策
  const sendPermissionDecision = useCallback((requestId: string, decision: 'allow' | 'deny') => {
    if (!backendRef.current) return;
    backendRef.current.stdin.write(JSON.stringify({ type: 'permission_decision', request_id: requestId, decision }) + '\n');
  }, []);
  
  return {
    sendPrompt,
    sendPermissionDecision,
  };
}

function findProjectDir(): string {
  // 从当前目录向上查找项目根目录
  let dir = process.cwd();
  while (dir !== '/') {
    if (fs.existsSync(path.join(dir, '.nocode')) || fs.existsSync(path.join(dir, 'pyproject.toml'))) {
      return dir;
    }
    dir = path.dirname(dir);
  }
  return process.cwd();
}