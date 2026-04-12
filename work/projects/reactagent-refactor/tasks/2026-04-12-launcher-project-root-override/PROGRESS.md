# 修复 launcher 继承错误项目根 进度

任务编号：`2026-04-12-launcher-project-root-override`
所属项目：`reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-launcher-project-root-override`

## 当前状态

- 状态：`已完成`
- 最近更新时间：`2026-04-12`

## 已完成

- 已创建任务档案
- 已复现并确认问题来自外部残留的错误 `NOCODE_PROJECT_DIR`
- 已将 `nocode` 改为强制绑定当前仓库项目根
- 已新增 launcher 环境变量污染回归测试
- 已通过全量 `unittest` 回归

## 进行中

- 无

## 待做

- 无

## 决策记录

- `nocode` 作为项目绑定 launcher，不应继承 shell 外部残留的 `NOCODE_PROJECT_DIR`
- 项目根以脚本真实所在仓库为准，比沿用外部环境变量更安全
- 保留用户当前工作目录，但不保留错误的项目根注入

## 风险与阻塞

- 当前工作树仍有用户自己的 `AGENTS.md` 未提交改动，提交时必须排除
