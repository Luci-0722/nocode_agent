# TUI ANSI Stream And Scrollback

## 背景

TUI 之前有两个相关显示问题：

- 流式输出中如果 ANSI 真彩色序列被拆 chunk，前端偶尔会把残片直接渲染出来，例如 `[38;2;186;198;207m_c`
- transcript 视图按“消息条数”裁剪，不按“渲染行数”裁剪，长消息很多时向上翻页只能看到半截内容

这两个问题都属于显示层与流式输入/布局模型不一致，而不是简单样式 bug。

## 实现

### 1. 流式 ANSI 处理前移到接收层

新增 `frontend/ansiStream.ts`：

- `AnsiTextStream` 在文本流入口维护 pending buffer
- 遇到不完整的 `ESC[` 控制序列时，先缓存，等待下一个 chunk
- 只有完整控制序列才会被吞掉；普通文本才会继续流向 TUI
- `sanitizeAnsiText()` 用于处理历史消息等非流式完整文本

接入点在 `frontend/hooks/useBackend.ts` 的 `text` 事件处理处，而不是继续依赖显示层 `stripAnsi()` 打补丁。

### 2. Transcript 改为按渲染行维护 scrollback

新增 `frontend/messageLines.ts`，把消息渲染逻辑抽成可复用的“按行展开”函数：

- assistant/user/system/tool 都先展开为最终可显示的字符串行
- `Transcript` 基于这些行构建 viewport
- `transcriptScroll` 现在表示“离底部的行偏移”而不是“消息偏移”
- `PageUp/PageDown` 改为按页滚动
- tool 选中状态仍会自动滚动到可视区内

这意味着应用内历史视图可以完整浏览长消息，不再受单条消息高度影响。

## 验证

- `npm --prefix frontend run build`
- `python3 -m unittest discover -s tests -v`

## 影响范围

- `frontend/hooks/useBackend.ts`
- `frontend/components/Transcript.tsx`
- `frontend/App.tsx`
- `frontend/messageLines.ts`
- `frontend/ansiStream.ts`
