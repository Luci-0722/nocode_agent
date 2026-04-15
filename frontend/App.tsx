import React, { useMemo, useState } from 'react';
import { Box, Text, useApp, useInput, useStdin } from 'ink';
import Composer from './components/Composer.js';
import Header from './components/Header.js';
import ModelPicker from './components/ModelPicker.js';
import PermissionDialog from './components/PermissionDialog.js';
import QuestionDialog from './components/QuestionDialog.js';
import StatusBar from './components/StatusBar.js';
import ThreadPicker from './components/ThreadPicker.js';
import Transcript from './components/Transcript.js';
import { useAppState } from './hooks/useAppState.js';
import { useBackend } from './hooks/useBackend.js';
import { buildSlashCommandHelpText } from './slashCommands.js';
import type { ModelOption, PermissionRequestState, QuestionRequestState } from './hooks/useAppState.js';
import type { ThreadInfo } from './types/events.js';

interface Props {
  resume?: boolean;
  model?: string;
}

function makeSystemMessage(content: string) {
  return {
    id: `system-local-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    kind: 'message' as const,
    role: 'system' as const,
    content,
    timestamp: Date.now(),
  };
}

function isPrintableInput(input: string, key: { ctrl?: boolean; meta?: boolean }): boolean {
  return Boolean(input) && !key.ctrl && !key.meta && !/[\u0000-\u001f\u007f]/.test(input);
}

export default function App({ resume = false, model }: Props) {
  const { exit } = useApp();
  const { stdin } = useStdin();
  const backend = useBackend({ resume, model });
  const [input, setInput] = useState('');

  const {
    addMessage,
    generating,
    messages,
    modelOptions,
    modelPickerIndex,
    modelPickerOpen,
    permissionPreference,
    permissionRequest,
    questionRequest,
    selectedToolId,
    setPermissionPreference,
    setQuestionRequest,
    setPermissionRequest,
    setSelectedToolId,
    setTranscriptScroll,
    threadPickerIndex,
    threadPickerOpen,
    threads,
    toggleToolExpanded,
    updatePermissionRequest,
    updateQuestionRequest,
    moveModelPicker,
    closeModelPicker,
    moveThreadPicker,
    closeThreadPicker,
  } = useAppState();

  const selectableTools = useMemo(
    () => messages.filter((message) => message.kind === 'tool'),
    [messages],
  );

  const overlayActive = modelPickerOpen || threadPickerOpen || !!permissionRequest || !!questionRequest;
  const composerDisabled = generating || overlayActive;

  const cycleToolSelection = (direction: 1 | -1) => {
    if (selectableTools.length === 0) {
      return;
    }
    if (!selectedToolId) {
      setSelectedToolId(selectableTools[Math.max(0, direction > 0 ? 0 : selectableTools.length - 1)].id);
      return;
    }
    const index = selectableTools.findIndex((tool) => tool.id === selectedToolId);
    const nextIndex =
      index < 0
        ? 0
        : Math.max(0, Math.min(selectableTools.length - 1, index + direction));
    setSelectedToolId(selectableTools[nextIndex].id);
  };

  const appendLocalSystem = (content: string) => {
    addMessage(makeSystemMessage(content));
  };

  const handleHelp = () => {
    appendLocalSystem(buildSlashCommandHelpText());
  };

  const handleSlashCommand = (raw: string): boolean => {
    const trimmed = raw.trim();
    if (!trimmed.startsWith('/')) {
      return false;
    }

    const [command, ...rest] = trimmed.slice(1).split(/\s+/);
    const arg = rest.join(' ').trim();

    switch (command) {
      case 'help':
        handleHelp();
        return true;
      case 'clear':
        backend.clearConversation();
        setInput('');
        return true;
      case 'session':
      case 'status':
        backend.requestStatus();
        return true;
      case 'resume':
        backend.listThreads();
        return true;
      case 'models':
        if (arg) {
          backend.switchModel(arg);
        } else {
          backend.listModels();
        }
        return true;
      case 'cancel':
        backend.cancel();
        return true;
      case 'permission':
      case 'perm':
        if (arg === 'ask' || arg === 'all') {
          setPermissionPreference(arg);
          appendLocalSystem(`Permission mode set to ${arg}.`);
        } else {
          appendLocalSystem('Usage: /permission ask|all');
        }
        return true;
      case 'quit':
      case 'exit':
        exit();
        return true;
      default:
        appendLocalSystem(`Unknown command: /${command}`);
        return true;
    }
  };

  const handleSubmit = (value: string) => {
    if (!value.trim() || generating) {
      return;
    }
    if (handleSlashCommand(value)) {
      setInput('');
      return;
    }
    backend.sendPrompt(value);
    setInput('');
  };

  const submitPermissionRequest = (request: PermissionRequestState) => {
    backend.sendPermissionDecisions(request.requestId, request.decisions);
    setPermissionRequest(null);
  };

  const selectCurrentModel = (options: ModelOption[], index: number) => {
    const selected = options[index];
    if (!selected) {
      return;
    }
    backend.switchModel(selected.name);
    closeModelPicker();
  };

  const selectCurrentThread = (items: ThreadInfo[], index: number) => {
    const selected = items[index];
    if (!selected) {
      return;
    }
    closeThreadPicker();
    backend.resumeThread(selected.thread_id);
  };

  const advanceQuestion = (request: QuestionRequestState, answer: string) => {
    const question = request.questions[request.questionIndex];
    const line = `${question.question} -> ${answer}`;
    const nextAnswers = [...request.answers, line];
    if (request.questionIndex >= request.questions.length - 1) {
      backend.sendQuestionAnswer(nextAnswers.join('\n'));
      setQuestionRequest(null);
      return;
    }
    setQuestionRequest({
      ...request,
      questionIndex: request.questionIndex + 1,
      optionIndex: 0,
      selectedOptions: [],
      textAnswer: '',
      answers: nextAnswers,
    });
  };

  const commitQuestionAnswer = (request: QuestionRequestState) => {
    const current = request.questions[request.questionIndex];
    const options = current.options || [];
    const answer = options.length > 0
      ? current.multiSelect
        ? (request.selectedOptions.length > 0
            ? request.selectedOptions
            : options[request.optionIndex]
              ? [options[request.optionIndex].label]
              : [])
        : (options[request.optionIndex] ? [options[request.optionIndex].label] : [])
      : request.textAnswer.trim()
        ? [request.textAnswer.trim()]
        : [];

    if (answer.length === 0) {
      return;
    }
    advanceQuestion(request, answer.join(', '));
  };

  useInput((keyInput, key) => {
    if (key.ctrl && keyInput === 'c') {
      exit();
      return;
    }

    if (modelPickerOpen) {
      if (key.escape) {
        closeModelPicker();
        return;
      }
      if (key.upArrow) {
        moveModelPicker(-1);
        return;
      }
      if (key.downArrow) {
        moveModelPicker(1);
        return;
      }
      if (key.return) {
        selectCurrentModel(modelOptions, modelPickerIndex);
      }
      return;
    }

    if (threadPickerOpen) {
      if (key.escape) {
        closeThreadPicker();
        return;
      }
      if (key.upArrow) {
        moveThreadPicker(-1);
        return;
      }
      if (key.downArrow) {
        moveThreadPicker(1);
        return;
      }
      if (key.return) {
        selectCurrentThread(threads, threadPickerIndex);
      }
      return;
    }

    if (permissionRequest) {
      if (key.upArrow || key.leftArrow) {
        updatePermissionRequest((request) => ({
          ...request,
          optionIndex: Math.max(0, request.optionIndex - 1),
        }));
        return;
      }
      if (key.downArrow || key.rightArrow) {
        updatePermissionRequest((request) => ({
          ...request,
          optionIndex: Math.min(1, request.optionIndex + 1),
        }));
        return;
      }
      if (key.return) {
        const currentAction = permissionRequest.actions[permissionRequest.actionIndex];
        const option = permissionRequest.optionIndex === 0 ? 'approve' : 'reject';
        const nextRequest: PermissionRequestState = {
          ...permissionRequest,
          decisions: [...permissionRequest.decisions, { type: option }],
        };
        if (permissionRequest.actionIndex >= permissionRequest.actions.length - 1) {
          submitPermissionRequest(nextRequest);
          return;
        }
        setPermissionRequest({
          ...nextRequest,
          actionIndex: permissionRequest.actionIndex + 1,
          optionIndex: currentAction.allowed_decisions.includes('approve') ? 0 : 1,
        });
      }
      return;
    }

    if (questionRequest) {
      const current = questionRequest.questions[questionRequest.questionIndex];
      const options = current?.options || [];
      if (options.length > 0) {
        if (key.upArrow) {
          updateQuestionRequest((request) => ({
            ...request,
            optionIndex: Math.max(0, request.optionIndex - 1),
          }));
          return;
        }
        if (key.downArrow) {
          updateQuestionRequest((request) => ({
            ...request,
            optionIndex: Math.min(options.length - 1, request.optionIndex + 1),
          }));
          return;
        }
        if (current.multiSelect && keyInput === ' ') {
          updateQuestionRequest((request) => {
            const label = options[request.optionIndex]?.label;
            if (!label) {
              return request;
            }
            return {
              ...request,
              selectedOptions: request.selectedOptions.includes(label)
                ? request.selectedOptions.filter((item) => item !== label)
                : [...request.selectedOptions, label],
            };
          });
          return;
        }
        if (key.return) {
          commitQuestionAnswer(questionRequest);
        }
        return;
      }

      if (key.escape) {
        setQuestionRequest(null);
        return;
      }
      if (key.return) {
        commitQuestionAnswer(questionRequest);
        return;
      }
      if (key.backspace || key.delete) {
        updateQuestionRequest((request) => ({
          ...request,
          textAnswer: request.textAnswer.slice(0, -1),
        }));
        return;
      }
      if (isPrintableInput(keyInput, key)) {
        updateQuestionRequest((request) => ({
          ...request,
          textAnswer: request.textAnswer + keyInput,
        }));
      }
      return;
    }

    if ((key.ctrl && keyInput === 'j') || (key.ctrl && keyInput === 'n')) {
      cycleToolSelection(1);
      return;
    }
    if (key.ctrl && keyInput === 'p') {
      cycleToolSelection(-1);
      return;
    }
    if (key.ctrl && keyInput === 'o' && selectedToolId) {
      toggleToolExpanded(selectedToolId);
      return;
    }
    if (key.pageUp) {
      setTranscriptScroll((value) => value + 1);
      return;
    }
    if (key.pageDown) {
      setTranscriptScroll((value) => Math.max(0, value - 1));
      return;
    }
    if (key.escape && generating) {
      backend.cancel();
    }
  }, { isActive: stdin.isTTY });

  if (!stdin.isTTY) {
    return (
      <Box flexDirection="column">
        <Text color="red">Error: this program must run in a TTY.</Text>
        <Text>Run with: ./nocode-ink</Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" height="100%">
      <Header />
      <Box flexGrow={1} flexDirection="column">
        <Transcript />
      </Box>
      {modelPickerOpen && <ModelPicker />}
      {threadPickerOpen && <ThreadPicker />}
      {permissionRequest && <PermissionDialog />}
      {questionRequest && <QuestionDialog />}
      <Composer
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        disabled={composerDisabled}
      />
      <StatusBar />
    </Box>
  );
}
