# TUI Transcript Scrollback

## 背景

TUI 的 transcript 曾经是 Ink 渲染的固定高度应用视口，只显示 `logo` 和输入框之间的一页内容。

这个模型在 Windows PowerShell 里很容易造成误解：终端滚轮看起来只能看到一页，因为历史内容没有作为自然增长的终端输出保留下来。

## 问题

固定视口带来两个问题：

- 用户希望像普通 CLI 一样用终端 scrollback 查看所有历史消息
- `selectedToolId` 曾经会影响可视窗口位置，导致后续 assistant 内容已经进入 state，但看起来像没有显示

## 本次调整

- `Transcript` 不再按终端高度裁剪消息
- 根布局不再固定为 `height="100%"`
- transcript 区域不再使用 `flexGrow` 占据一页固定空间
- 移除 `PageUp` / `PageDown` 的应用内 viewport 快捷键提示与处理

## 结果

- 所有消息都会正常追加到终端输出流中
- 终端原生滚动条可以查看之前的消息
- 工具选择只影响高亮与展开，不再限制后续内容显示

## 验证

- `npm --prefix frontend run build`
