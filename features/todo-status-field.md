# Todo 状态字段

## 功能概述

为 `todo_write` 工具的待办事项添加独立 `status` 字段，支持三种状态：

- `pending` — 待办（□）
- `in_progress` — 进行中（◐）
- `completed` — 已完成（■）

## 设计动机

之前的实现使用简单字符串数组，通过比较新旧列表推断完成状态：

```json
// 旧格式
{"todos": ["Step 1: 实现", "Step 2: 测试", "Step 3: 部署"]}
```

**问题**：

1. 内容变化导致误判 — `"Step 1: 实现"` 和 `"Step 1: 实现 - 完成"` 被认为是不同任务
2. 无法区分进行中状态
3. 无法精确显示完成进度

参考 Claude Code 的 todo 实现（`claude-code-analysis/src/utils/todo/types.ts`），每个 item 应有独立 status 字段。

## 实现细节

### 后端改动

**位置**：`src/nocode_agent/tool/interactive.py`

**新增 TodoItem 类**：

```python
class TodoItem(BaseModel):
    content: str = Field(description="待办事项内容。")
    status: str = Field(default="pending", description="状态：pending、in_progress 或 completed。")


class TodoInput(BaseModel):
    todos: list[TodoItem] = Field(description="待办事项列表。")
```

**todo_write 输出格式**：

```
待办列表已更新：
- ■ Step 1: 实现功能
- ◐ Step 2: 测试
- □ Step 3: 部署
```

状态符号映射：
- `pending` → `□`（空心方框）
- `in_progress` → `◐`（半填充圆）
- `completed` → `■`（实心方框）

---

### 前端改动

**位置**：旧实现位于 `frontend/tui.ts`，迁移后由 Ink transcript/tool renderer 承载

**getTodoItemsFromTool 改动**：

```typescript
// 返回类型从 string[] 改为 { content: string; status: string }[]
private getTodoItemsFromTool(tool: ToolCall): { content: string; status: string }[] {
  const rawTodos = tool.args?.todos;
  if (Array.isArray(rawTodos)) {
    // 新格式：{ content, status } 对象数组
    const newFormat = rawTodos.filter(
      (item): item is { content: string; status: string } =>
        typeof item === "object" && item !== null && typeof item.content === "string"
    );
    if (newFormat.length > 0) {
      return newFormat.map((item) => ({
        content: item.content.trim(),
        status: typeof item.status === "string" ? item.status : "pending",
      }));
    }
    // 兼容旧格式：字符串数组
    return rawTodos
      .filter((item): item is string => typeof item === "string")
      .map((item) => ({ content: item.trim(), status: "pending" }));
  }
  // ...
}
```

**renderPlanToolBlock 改动**：

- 移除 `getPreviousPlanTodos` 和推断逻辑
- 直接根据每个 item 的 status 显示对应符号
- 已完成项显示在列表末尾，使用灰色样式

```typescript
// 先显示待办和进行中的任务
for (const item of pendingItems) {
  const mark = item.status === "in_progress" ? "◐" : "□";
  // ...
}

// 再显示已完成的任务（灰色）
for (const item of completedItems) {
  // 使用 ■ 符号
  // ...
}
```

---

## 工具 Schema

```json
{
  "$defs": {
    "TodoItem": {
      "properties": {
        "content": {
          "description": "待办事项内容。",
          "type": "string"
        },
        "status": {
          "default": "pending",
          "description": "状态：pending、in_progress 或 completed。",
          "type": "string"
        }
      },
      "required": ["content"],
      "type": "object"
    }
  },
  "properties": {
    "todos": {
      "description": "待办事项列表。",
      "items": { "$ref": "#/$defs/TodoItem" },
      "type": "array"
    }
  },
  "required": ["todos"],
  "type": "object"
}
```

---

## 调用示例

**模型调用**：

```json
{
  "name": "todo_write",
  "args": {
    "todos": [
      {"content": "Step 1: 实现功能", "status": "completed"},
      {"content": "Step 2: 测试", "status": "in_progress"},
      {"content": "Step 3: 部署", "status": "pending"}
    ]
  }
}
```

**TUI 显示**：

```
• Updated Plan
  └ Step 2: 测试；Step 3: 部署
    ◐ Step 2: 测试
    □ Step 3: 部署
    ■ Step 1: 实现功能
```

---

## 向后兼容

前端兼容两种格式：

1. **新格式** — `{ content, status }[]` 对象数组
2. **旧格式** — `string[]` 字符串数组（自动转为 `status: "pending"`）

模型端需更新调用方式，传入带 status 的对象数组。

---

## 文件改动

| 文件 | 改动 |
|------|------|
| `src/nocode_agent/tool/interactive.py` | 新增 `TodoItem` 类；修改 `todo_write`、`todo_read` |
| `src/nocode_agent/tool/__init__.py` | 导出 `TodoItem` |
| `frontend/components/Message.tsx` 等 Ink renderer | 承接 todo 工具结果展示逻辑 |

---

## 与 Claude Code 对比

| 维度 | nocode_agent | Claude Code |
|------|--------------|-------------|
| status 字段 | ✅ pending/in_progress/completed | ✅ pending/in_progress/completed |
| activeForm 字段 | ❌ 未实现 | ✅ 进行中时的动态描述 |
| 清空逻辑 | 手动调用空数组 | 全部完成自动清空 |
| verification nudge | ❌ 未实现 | ✅ 3+ 项完成时提示调用验证 agent |

---

## 后续改进方向

1. **activeForm 字段** — 进行中任务可显示动态描述（如"正在修改 kit.py"）
2. **自动清空** — 全部完成时自动清空列表
3. **verification nudge** — 类似 Claude Code，完成多项任务后提示调用验证 agent

---

## 参考资料

- Claude Code TodoItem 类型：`claude-code-analysis/src/utils/todo/types.ts`
- Claude Code TodoWriteTool：`claude-code-analysis/src/tools/TodoWriteTool/TodoWriteTool.ts`
