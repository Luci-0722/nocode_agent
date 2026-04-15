# Plan

## Current Phase

Phase 2: 核心组件完善

## Next Bounded Steps

1. 完善 Composer 输入处理（使用 ink-text-input 或实现完整的输入逻辑）
2. 实现 ANSI 渲染组件（处理流式输出中的 ANSI 序列）
3. 完善流式输出显示（增量更新、自动滚动）
4. 实现输入历史记录（上下箭头）
5. 测试交互流程（启动后端、发送提示词、接收响应）

## Open Questions

- ink-text-input 是否能正常工作？（需要测试）
- 是否需要自定义 ANSI 渲染？（参考 Claude Code 的 Ansi.tsx）
- 如何处理多行输入？（Shift+Enter）
- 如何处理工具调用的详细显示？