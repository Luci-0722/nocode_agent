# 多模型配置

## 功能概述

支持在项目 `.nocode/config.yaml` 或全局 `~/.nocode/config.yaml` 中配置多个模型，通过 `/models` 命令在会话间切换，无需修改配置文件或重启。

## 设计动机

不同任务适合不同模型：
- 日常对话：快速、低成本模型
- 复杂推理：高能力模型
- 本地开发：Ollama 等本地模型
- 多云部署：切换不同云服务商 API

原有方案需要修改配置文件并重启，体验不连贯。

## 配置格式

```yaml
# 多模型配置
models:
  glm:
    model: glm-5.1
    base_url: "https://open.bigmodel.cn/api/coding/paas/v4"
    # api_key 省略则从 ZHIPU_API_KEY 环境变量读取

  qwen:
    model: qwen3-coder-plus
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # api_key 省略则从 DASHSCOPE_API_KEY 环境变量读取

  claude:
    model: claude-sonnet-4
    base_url: "https://api.anthropic.com"
    # api_key 省略则从 ANTHROPIC_API_KEY 环境变量读取

  ollama:
    model: qwen2.5-coder:14b
    base_url: "http://127.0.0.1:11434/v1"

# 默认使用的模型（对应 models 中的 key）
default_model: glm
```

## 命令交互

### 列出可用模型

```
> /models
可用模型:
  claude
  glm (当前) (默认)
  ollama
  qwen

使用 /models <名称> 切换模型
```

### 切换模型

```
> /models qwen
已切换到模型 qwen (qwen3-coder-plus)
```

### 切换时机

- **会话进行中**：禁止切换（Agent 实例正在使用当前模型）
- **会话结束后**：允许切换，下次对话使用新模型

## 实现细节

### 配置解析

**位置**：`src/nocode_agent/config/__init__.py`

**新增函数**：
- `list_available_models(config)` — 列出所有配置的模型名称
- `resolve_model_config(config, model_name)` — 解析指定模型的配置参数

**解析逻辑**：
```python
def resolve_model_config(config: dict, model_name: str | None = None) -> dict:
    models_section = config.get("models", {})
    target_name = model_name or config.get("default_model")

    if not target_name or target_name not in models_section:
        raise ValueError(f"Model '{target_name}' not found")

    model_cfg = models_section[target_name]
    return {
        "model": model_cfg.get("model", ""),
        "base_url": model_cfg.get("base_url", ""),
        "api_key": model_cfg.get("api_key", ""),
    }
```

### Agent 创建

**位置**：`src/nocode_agent/runtime/bootstrap.py`

**改动**：
- `build_mainagent_kwargs(config, model_name=None)` — 新增 `model_name` 参数
- `create_agent_from_config(config, model_name=None)` — 支持指定模型创建 Agent

### 后端命令处理

**位置**：`src/nocode_agent/app/backend_stdio.py`

**新增消息类型**：
- `list_models` — 返回可用模型列表
- `switch_model` — 切换模型（仅在非生成状态时生效）

**状态管理**：
- `_current_model_name` — 当前模型配置名称
- `_generating` — 是否正在生成（生成中禁止切换）

### 前端命令

**位置**：`frontend/App.tsx`、`frontend/hooks/useBackend.ts`、`frontend/hooks/useAppState.ts`

**新增**：
- `SlashCommandAction` 新增 `"models"` 类型
- `SLASH_COMMANDS` 新增 `/models` 命令定义
- `handleModelsCommand()` — 处理命令输入
- 状态栏显示模型名称（如 `glm (glm-5.1)`）

---

## 文件改动

| 文件 | 改动 |
|------|------|
| `config.example.yaml` | 新增 `models` 配置段示例 |
| `src/nocode_agent/config/__init__.py` | 新增 `list_available_models()`, `resolve_model_config()` |
| `src/nocode_agent/runtime/bootstrap.py` | `build_mainagent_kwargs()` 支持 `model_name` 参数 |
| `src/nocode_agent/app/backend_stdio.py` | 新增 `list_models`, `switch_model` 消息处理 |
| `frontend/App.tsx` / `frontend/hooks/useBackend.ts` | 新增 `/models` 命令与模型选择器状态同步 |

---

## 记忆与切换

**问题**：切换模型后，之前的对话记忆是否保留？

**答案**：保留。

记忆存储在 SQLite checkpoint 数据库中，通过 `thread_id` 标识。切换模型时：
1. 销毁当前 Agent 实例
2. 使用新模型配置重建 Agent
3. 保持相同的 `thread_id` 和 checkpoint 路径

新 Agent 会从 checkpoint 恢复历史消息，记忆完整保留。

**限制**：运行中的会话不能切换模型，必须等待当前对话结束。

---

## API Key 推断规则

每个模型配置的 `api_key` 字段可省略，系统会按以下顺序推断：

1. 配置中显式指定的 `api_key`
2. 环境变量（根据 provider 推断）
   - GLM → `ZHIPU_API_KEY`
   - Qwen → `DASHSCOPE_API_KEY`
   - Claude → `ANTHROPIC_API_KEY`
   - OpenAI 兼容 → `OPENAI_API_KEY`

---

## 后续改进方向

1. **运行时切换** — 支持在会话进行中切换模型（需要更复杂的状态管理）
2. **模型别名** — 支持短别名如 `/models fast`、`/models smart`
3. **自动选择** — 根据任务复杂度自动选择合适模型
4. **成本统计** — 显示每个模型的 token 消耗和费用

---

## 与 Claude Code 对比

| 维度 | nocode_agent | Claude Code |
|------|--------------|-------------|
| 多模型配置 | ✅ YAML 配置 | ❌ 仅单模型 |
| 运行时切换 | ✅ `/models` 命令 | ❌ 需重启 |
| 记忆保留 | ✅ 切换后保留 | N/A |
| API Key 推断 | ✅ 按环境变量 | ✅ 环境变量 |
