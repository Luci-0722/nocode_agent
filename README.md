# nocode_agent

`nocode_agent` 是一个独立的 NoCode coding agent 运行时仓库，基于 LangChain / LangGraph 构建，当前采用 Python backend + TypeScript TUI 的结构。

它的目标很直接：在终端里提供一个可运行、可恢复、可扩展的 coding agent，支持多模型接入、subagent、skills、权限审批，以及长会话压缩。

## 适合什么场景

- 在终端里直接使用 coding agent 处理代码和工程任务
- 需要一个可本地运行、可改造的 agent runtime
- 想要按项目隔离配置、状态和 subagent 定义
- 想在现有实现上继续开发 TUI、backend、skills 或运行时能力

## 当前能力

- TypeScript TUI，直接在终端中交互
- Python stdio backend，前后端职责清晰
- 基于 LangChain / LangGraph 构建 agent、tool 调用和运行时编排
- 支持恢复历史会话
- 支持项目级和用户级 subagent 发现
- 支持 skills 发现、恢复与调用
- 支持工具级 human-in-the-loop 审批
- backend 启动失败或异常退出时，TUI 会显示 `fatal`、最近 `stderr` 摘要和日志文件路径
- 支持 session memory 和 auto compact，缓解长上下文膨胀
- 支持 OpenAI 兼容接口、Anthropic 风格代理接口，以及本地 Ollama

## 项目结构

```text
src/nocode_agent/
  agent/          主 agent 构建与运行
  app/            stdio backend / ACP server 入口
  compression/    压缩、auto compact、session memory
  config/         配置读取与解析
  log/            日志初始化
  model/          模型工厂
  persistence/    checkpoint / 线程历史持久化
  prompt/         主提示词与上下文拼装
  runtime/        运行时路径、bootstrap、交互控制
  skills/         skills 发现、注册、恢复
  tool/           内建工具实现
  bundled_skills/ 仓库自带 skills

frontend/
  tui.ts
  input_protocol.ts
  terminal_utils.ts

.nocode/agents/   项目级 subagent 定义
tests/            启动与交互相关冒烟测试
```

## 技术栈

- LangChain / LangGraph
- Python backend
- TypeScript TUI
- SQLite checkpoint persistence

## 环境要求

- Python 3.10+
- Node.js

## 快速开始

1. 安装 Python 包（建议使用虚拟环境）：

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -e .
```

2. 准备配置文件：

```bash
cp config.example.yaml config.yaml
```

3. 修改 `config.yaml`，至少填好模型相关配置：

- `model`
- `base_url`
- `api_key`

4. 直接启动 TUI：

```bash
npx tsx frontend/tui.ts
```

恢复历史会话：

```bash
npx tsx frontend/tui.ts --resume
```

## 安装启动器

安装后可在任意目录直接输入 `nocode` 启动。

### Windows（PowerShell）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_nocode_launcher.ps1
```

脚本会把 `scripts\nocode.ps1` 复制到 `C:\Users\<用户名>\.local\bin\nocode.ps1` 并自动添加到用户 PATH。

安装完成后**打开新的 PowerShell 窗口**，直接运行：

```powershell
nocode
```

如需重新安装覆盖已有文件：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_nocode_launcher.ps1 -Force
```

### macOS / Linux

```bash
bash scripts/install_nocode_launcher.sh
```

脚本会把仓库根目录下的 `nocode` 软链接安装到 `~/.local/bin/nocode`。

安装完成后直接运行：

```bash
nocode
```

## 配置说明

配置文件按以下优先级查找：

1. 环境变量 `NOCODE_AGENT_CONFIG` / `NOCODE_CONFIG` / `BF_CONFIG` 指定的路径
2. 项目目录下的 `config.yaml`
3. 全局配置 `~/.nocode/config.yaml`

安装启动器后，建议将配置放到全局位置，这样在任意目录启动都能生效：

```bash
# 创建全局配置目录并复制示例配置
mkdir -p ~/.nocode
cp config.example.yaml ~/.nocode/config.yaml
```

然后修改 `~/.nocode/config.yaml`，至少填好模型相关配置：

- `model`
- `base_url`
- `api_key`

`config.example.yaml` 中已包含常见模型配置示例：

- GLM / 智谱
- 阿里百炼 OpenAI 兼容模式
- 阿里百炼 Anthropic 风格代理
- Ollama 本地模型

建议优先把密钥放到环境变量中，而不是直接写入配置文件。

示例配置默认把 checkpoint、ACP session 和 session memory 写到项目内的 `.state/` 路径下；如果你有自己的目录约定，也可以通过配置或环境变量覆盖。

常见环境变量：

- `NOCODE_PROJECT_DIR`
- `NOCODE_STATE_DIR`
- `NOCODE_AGENT_CONFIG`
- `NOCODE_LOG_FILE`
- `NOCODE_PROXY`
- `NOCODE_NO_PROXY`

## 日志与排障

当 backend 初始化失败或异常退出时，TUI 会直接在界面里展示排障信息，包括：

- `fatal: ...`
- `最近 stderr:`
- `日志文件: ...`

这样在启动失败时，不需要额外切换到别的终端就能先看到错误摘要和日志文件位置。

如果你希望显式指定日志文件路径，可以设置：

```bash
export NOCODE_LOG_FILE=/your/path/nocode.log
```

## Subagent

运行时会从以下位置发现 subagent：

- 项目级：`.nocode/agents/**/*.md`
- 用户级：`~/.nocode/agents/**/*.md`

最小示例：

```md
---
name: reviewer
description: 用于独立审查迁移、接口变更和高风险代码，适合在主实现完成后做一次独立验证
when_not_to_use: 简单改动或 1-2 个文件的小修复不需要单独委派审查
tools: [read, grep]
model: glm-5.1
---
你是一个代码审查子代理。
只做审查，不要修改文件。
重点关注行为回归、边界条件和缺失测试。
```

字段说明：

- `name`：`delegate_code` 使用的 subagent 类型名
- `description`：必填，用途说明，主 agent 选择 subagent 时会读取这里
- `when_not_to_use`：可选，描述什么情况下不应该使用这个 subagent
- `tools`：可选，限制允许的工具
- `disallowedTools`：可选，显式禁用的工具
- `model`：可选，覆盖默认 `subagent_model`

## 开发

运行最小冒烟测试：

```bash
python3 -m unittest discover -s tests -v
```

单独调试 backend：

```bash
PYTHONPATH=src python3 -m nocode_agent.app.backend_stdio
```

TUI、启动器、路径解析、backend 启动相关改动，优先关注：

- `frontend/tui.ts`
- `frontend/input_protocol.ts`
- `frontend/terminal_utils.ts`
- `src/nocode_agent/runtime/paths.py`
- `tests/test_startup_smoke.py`

## 仓库定位

这个仓库当前专注于 agent runtime 本身，主要包括：

- Python agent/backend
- 终端 TUI
- subagent / skills / 权限审批
- 持久化与长上下文压缩

当前不包含：

- Web UI
- 多会话编排平台
- 独立的会话注册表服务
