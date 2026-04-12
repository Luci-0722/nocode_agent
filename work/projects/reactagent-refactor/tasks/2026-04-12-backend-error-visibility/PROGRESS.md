# 改善 TUI 中 backend 错误可见性 进度

任务编号：`2026-04-12-backend-error-visibility`
所属项目：`reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-backend-error-visibility`

## 当前状态

- 状态：`已完成`
- 最近更新时间：`2026-04-12`

## 已完成

- 已创建任务档案
- 已确认当前 TUI 会吞掉 backend stderr，只保留 `backend exited with code ...`
- 已确认 backend 日志默认写入项目根 `.state/nocode.log`
- 已在 TUI 中缓存 backend 最近 stderr，并在 fatal / 非零退出时展示
- 已新增 PTY 冒烟测试，覆盖 fake backend fatal + stderr 场景
- 已通过 `node --check`、`unittest`、`compileall` 与 `git diff --check`

## 进行中

- 无

## 待做

- 无

## 决策记录

- 保持 TUI 平时不直播 backend stderr，只在 fatal / 非零退出时显示最近摘要
- 同时显示日志文件路径，给用户明确的排障入口
- 测试采用 Python 标准库 PTY 驱动真实 TUI，而不是引入额外前端测试框架
- 如果 backend 已主动发送 `fatal`，则抑制后续重复的 `code 1` 退出提示

## 风险与阻塞

- TUI 是全屏终端界面，PTY 测试对 ANSI 输出较敏感，但当前断言只匹配关键文本，稳定性可接受
