# TUI 启动阶段改为显式 Loading 态

## 背景

TUI 进程会先把 Ink 界面渲染出来，再异步拉起 Python backend，并等待 backend 发回第一条 `hello/status` 事件。

在 Windows 上，这个窗口更明显：界面已经出现，但 `thread` 还是空的。此时如果用户立刻开始输入，会误以为已经可以发送。

## 本次调整

- `threadId` 未就绪时，Transcript 显示“正在连接 backend”的 loading 文案
- `threadId` 未就绪时，不渲染输入框
- 状态栏在启动窗口显示 `Backend loading...`
- 即使通过异常路径触发提交，前端也会拦截并提示 backend 仍在加载

## 结果

- backend 完成握手前，界面不再暴露“可输入但不可发送”的假状态
- 避免启动竞态导致的消息丢失和 `generating` 长时间悬挂
- Windows 上的慢启动表现更可理解，用户能明确看到当前仍在初始化

## 验证

- `npm --prefix frontend run build`
