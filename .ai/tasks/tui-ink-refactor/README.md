# tui-ink-refactor

## Goal

TUI 重构：将当前 4500+ 行手写终端 UI 迁移到 Ink (React for CLI) 框架，实现声明式组件架构，支持历史记录、ANSI 完整渲染、跨终端兼容。

## Scope

**包含：**
- 使用 Ink 框架重构旧的 `frontend/tui.ts`，迁移到 `frontend/index.tsx` + `frontend/App.tsx`
- 创建 React 组件架构（App、Header、Transcript、Composer、StatusBar 等）
- 实现输入历史记录（上下箭头查看历史）
- 实现 ANSI 完整渲染（解决分片残留问题）
- 实现虚拟滚动（解决 PyCharm 终端滚动问题）
- 实现工具调用显示（ToolCall）
- 实现模型选择器（ModelPicker）
- 实现权限对话框（PermissionDialog）
- 保持后端协议不变（backend_stdio、事件类型）
- 测试跨终端兼容性（VSCode、PyCharm、iTerm2、Terminal.app）

**不包含：**
- 后端 Python 代码修改
- 配置文件格式变更
- 启动脚本逻辑变更（只改入口）
- 新增功能特性（只迁移现有功能）

## Non-goals

- 不修改后端协议或事件类型定义
- 不改变用户交互流程
- 不添加新的命令或功能
- 不修改配置系统
- 不涉及 MCP 或 skills 相关代码

## Completion Criteria

1. 所有现有功能正常工作：
   - 输入提示词并收到响应
   - 工具调用显示（状态、参数、输出）
   - 模型切换
   - 权限请求处理
   - 会话恢复

2. 新增功能正常工作：
   - 输入历史记录（上下箭头）
   - ANSI 完整渲染（无残留字符）
   - 跨终端兼容（VSCode、PyCharm、iTerm2）

3. 代码量显著减少：
   - frontend/ 目录总行数 < 1000 行
   - 无手写终端处理代码

4. 测试通过：
   - 启动冒烟测试
   - 各终端手动测试
