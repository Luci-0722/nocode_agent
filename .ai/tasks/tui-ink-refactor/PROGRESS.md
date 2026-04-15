# Progress

## Current Status

Phase 3 进行中，核心链路已可启动验证

## Latest Verification

- TypeScript 编译成功
- 修复了 `tsconfig.json` 的 `noEmit: true`，`nocode-ink` 现在会运行新的 Ink `dist/` 产物
- `./nocode-ink --resume` 已能启动新 Ink UI，并弹出 resume picker
- 选中历史线程后可恢复 transcript，基础会话恢复链路已打通

## Work Log

### 2026-04-15

**Phase 1: 基础框架**
- ✅ 安装 Ink 及相关依赖
- ✅ 创建 package.json 和 tsconfig.json
- ✅ 创建 hooks/useAppState.ts（Zustand 状态管理）
- ✅ 创建 types/events.ts（后端事件类型）
- ✅ 创建 hooks/useBackend.ts（后端通信）
- ✅ 创建 App.tsx（主应用骨架）
- ✅ 创建基础组件（Header、Transcript、Message、Composer、StatusBar）
- ✅ 创建 nocode-ink 启动脚本

**Phase 2: 核心组件完善**
- ✅ 完善 Composer 输入处理（上下箭头历史、Backspace、Ctrl+U/W）
- ✅ 实现 Ansi 组件（ANSI 序列解析和渲染）
- ✅ 集成 Ansi 到 Transcript（流式输出）
- ✅ TypeScript 编译成功

**下一步：Phase 3 测试**
- 在交互式终端中测试 nocode-ink
- 验证后端通信、输入、流式输出
- 测试历史记录功能
- 测试 ANSI 渲染

**Phase 3: 交互链路迁移**
- ✅ 重写 `useAppState`，把消息、overlay、model/thread picker、permission/question 状态收敛到单一 store
- ✅ 重写 `useBackend`，补齐 `model_list`、`thread_list`、`history`、`permission_request`、`question`、`token_usage` 等事件映射
- ✅ 新增 `DialogFrame`、`ModelPicker`、`ThreadPicker`、`PermissionDialog`、`QuestionDialog`
- ✅ `App` 改成 Claude Code 风格的主 REPL + 独立 dialog 结构
- ✅ 修复构建链路：`dist/` 不再是旧产物
- ⏳ 还需继续打磨 tool details、滚动体验和更多终端交互细节
