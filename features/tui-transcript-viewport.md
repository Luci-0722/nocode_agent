# TUI Transcript Viewport

## 背景

TUI 的 transcript 不是普通命令输出流，而是 Ink 渲染的固定高度应用视口。

因此在 Windows PowerShell 里，用终端原生滚轮查看历史并不可靠；历史查看应该走应用内 viewport，也就是 `PageUp` / `PageDown` 修改 `transcriptScroll`。

## 问题

此前 `Transcript` 会在存在 `selectedToolId` 时强制把可视窗口调整到选中的工具行附近。

这会导致一个错误行为：用户选中工具后，如果后面继续生成 assistant 内容，底部新内容已经进入 state，但可视窗口仍被选中工具锚住，看起来像 assistant 消息没有显示。

## 本次调整

- `transcriptScroll === 0` 时始终保持底部跟随最新内容
- 只有用户已经进入历史滚动状态时，才允许选中工具影响可视窗口

## 结果

- 选中工具不会阻止后续 assistant 内容显示在下面
- 工具选择仍然可以在历史浏览状态下辅助定位
- Windows / macOS 的 transcript 行为保持一致

## 验证

- `npm --prefix frontend run build`
