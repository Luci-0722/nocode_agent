# Dialog 样式收敛

## 背景

Ink TUI 的 transcript、header、status bar 已经使用仓库自己的配色体系，但 dialog 组件仍保留默认的 `cyan` 边框和选中态。

这会导致权限审批、问题提问、模型选择、会话恢复这些界面看起来像另一套 UI。

## 本次调整

调整文件：

- `frontend/components/DialogFrame.tsx`
- `frontend/components/PermissionDialog.tsx`
- `frontend/components/QuestionDialog.tsx`
- `frontend/components/ModelPicker.tsx`
- `frontend/components/ThreadPicker.tsx`

实现改为：

- dialog 外边框统一改为灰色
- 标题使用 TUI 自己的 accent 绿色
- 副标题使用 secondary 灰色
- 列表选中态去掉 `cyan`，统一改为绿色强调
- 问答输入框的边框和光标强调也同步去蓝色

## 验证

已执行：

```bash
npm --prefix frontend run build
```

建议继续手工验证：

- 触发一次权限审批，确认边框和选中态不再是蓝色
- 打开模型选择和恢复会话，确认 dialog 配色一致
- 打开问题提问，确认输入框光标强调色与 TUI 主风格一致
