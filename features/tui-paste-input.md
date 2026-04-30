# TUI Paste Input

TUI 输入区支持终端粘贴文本，包括多行内容。

## 行为

- Composer 启用 Ink `usePaste`，让 bracketed paste 内容作为完整文本进入输入框。
- 粘贴时保留正文、制表符和换行；`\r\n` 与 `\r` 会归一为 `\n`。
- 粘贴内容不会触发提交，用户仍需按 Enter 发送。
- 交互式提问弹窗的自由文本回答同样支持粘贴。
- 不支持粘贴输入的终端会走多字符输入兜底逻辑。

## 相关文件

- `frontend/input.ts`
- `frontend/components/Composer.tsx`
- `frontend/App.tsx`
