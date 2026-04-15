# Plan

## Current Phase

Phase 3: 交互链路迁移

## Next Bounded Steps

1. 继续补齐 tool details 的结构化展示，减少当前 JSON/raw output 的直出
2. 校准权限/提问对话框的交互细节，覆盖更多 edge cases
3. 继续测试 slash commands、模型切换、恢复会话、工具展开等实际终端行为
4. 评估是否需要更强的虚拟滚动/按行滚动，而不是当前消息级 viewport
5. 清理旧的 `frontend/tui.ts` 残留引用，准备切主入口

## Open Questions

- 现有消息级滚动在超长工具输出下是否足够，还是要引入更细粒度的 viewport
- 是否要继续兼容多行输入，还是保持 Claude Code 风格的单行 composer
- tool call 是否需要按不同工具类型拆专门 renderer，而不是统一卡片
