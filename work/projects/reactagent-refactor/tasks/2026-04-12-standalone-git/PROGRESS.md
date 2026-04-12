# 把 nocode_agent 拆成独立 git 仓库 进度

任务编号：`2026-04-12-standalone-git`
所属项目：`reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-standalone-git`

## 当前状态

- 状态：`已完成`
- 最近更新时间：`2026-04-12`

## 已完成

- 已创建任务档案
- 已确认当前 `nocode_agent/` 仍隶属于父仓库 `/Users/lucheng/Projects/NoCode`
- 已确定本轮采用“当前目录 fresh init 独立 git”方案，不改写父仓库历史
- 已在当前目录初始化独立 `.git/`
- 已补充独立仓库最小忽略规则，并排除私有 `config.yaml`
- 已更新 README 与项目级文档，说明新的仓库边界
- 已修正一条依赖旧 `PYTHON_BIN` 优先级的 PTY 冒烟测试，避免首提验证误报

## 进行中

- 无

## 待做

- 无

## 决策记录

- 这次只把 `nocode_agent/` 做成独立 git，不同时改造父仓库结构
- 这次不保留父仓库裁剪历史，先以当前工作树快照生成独立仓库首个提交
- 独立仓库建成后，默认在 `nocode_agent/` 目录内执行所有后续 `git` 操作
- `config.yaml` 含真实密钥，因此只保留 `config.example.yaml` 入库，`config.yaml` 改为本地忽略文件

## 风险与阻塞

- 父仓库仍会继续跟踪 `nocode_agent/` 中文件；如果回到父目录执行 `git status`，仍会看到这部分变更
- 如需连同旧提交历史一起拆分，后续还要单独做一次历史切分任务
- 当前独立仓库是 fresh init 首提，不包含父仓库历史
