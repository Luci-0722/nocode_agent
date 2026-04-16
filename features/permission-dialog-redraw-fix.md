# 审批弹窗重绘止血

## 背景

当工具调用触发审批时，TUI 会在 transcript 下方插入 `PermissionDialog`。

此前即使已经进入审批等待，底部 `Composer` 仍保持生成中 spinner 每 80ms 刷新一次。只要弹窗把整体高度挤出终端可视区，Ink 就会持续重绘并表现为“审批界面不断向下复制”。

## 本次调整

调整文件：

- `frontend/components/Composer.tsx`

实现改为：

- 当 `permissionRequest` 或 `questionRequest` 存在时，暂停生成中 spinner 的定时器
- 同时隐藏 `Generating (...)` 提示行
- 不改动现有审批协议、按键处理和后端事件

## 结果

这个改动只做止血，不改变交互模型。

它解决的是“审批等待期间高频重绘导致刷屏”的问题，让授权界面在当前布局下先稳定下来，方向键和 Enter 可以继续正常处理。

如果后续还要进一步对齐 Claude Code 风格，再把审批 UI 从独立 dialog 收敛成 transcript 内联块即可。

## 验证

已执行：

```bash
npm --prefix frontend run build
```

建议继续手工验证：

- 触发一次需要审批的工具调用，确认界面不再持续向下复制
- 在审批界面用 `↑/↓` 切换选项并用 `Enter` 确认
- 在提问界面确认同样不会触发 spinner 高频重绘
