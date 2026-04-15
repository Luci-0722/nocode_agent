import React from 'react';
import { Box, Text, useStdout } from 'ink';
import { useAppState } from '../hooks/useAppState.js';
import { COLOR, tildePath, truncate } from '../rendering.js';
import Ansi from './Ansi.js';

export default function StatusBar() {
  const { stdout } = useStdout();
  const {
    model,
    permissionPreference,
    questionRequest,
    reasoningEffort,
    threadId,
    tokensLeftPercent,
    transcriptScroll,
    cwd,
    modelPickerOpen,
    permissionRequest,
    threadPickerOpen,
    generating,
  } = useAppState();

  const width = Math.max(24, (stdout.columns || 80) - 2);
  const modelLabel = [model, reasoningEffort].filter(Boolean).join(' ') || '-';
  const contextLine = `${COLOR.secondary}${truncate(
    `thread ${threadId.slice(-8) || '--------'} · ${modelLabel} · ${tokensLeftPercent}% left · perm ${permissionPreference} · ${tildePath(cwd || '-')}`,
    width,
  )}${COLOR.reset}`;

  let hint = `Enter 发送  Shift+Enter 换行  Ctrl+N/P 选择工具  Ctrl+O 展开${transcriptScroll > 0 ? `  ↑${transcriptScroll}` : ''}`;
  if (modelPickerOpen || threadPickerOpen) {
    hint = '↑↓ 移动  Enter 选择  Esc 关闭';
  } else if (permissionRequest) {
    hint = '↑↓ 选择  Enter 确认';
  } else if (questionRequest) {
    hint = '↑↓ 选择  Space 切换  Enter 提交';
  } else if (!generating) {
    hint = `Enter 发送  Shift+Enter 换行  输入 / 打开命令  ↑↓ 选命令  Tab 补全  Ctrl+N/P 选工具${transcriptScroll > 0 ? `  ↑${transcriptScroll}` : ''}`;
  }

  return (
    <Box flexDirection="column" paddingX={1}>
      <Text> </Text>
      <Ansi>{contextLine}</Ansi>
      <Ansi>{`${COLOR.secondary}${truncate(hint, width)}${COLOR.reset}`}</Ansi>
    </Box>
  );
}
