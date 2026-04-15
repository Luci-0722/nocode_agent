# Ink TUI 样式回归

## 功能概述

将新的 Ink TUI 向旧版 `frontend/tui.ts` 的视觉和交互回归，优先恢复原有终端气质，而不是维持通用 CLI 插件面板风格。

本次回归重点包括：

- 恢复顶部 3 行 ASCII logo 和右侧 thread / model / cwd 信息
- 恢复生成中 spinner 与耗时显示
- 恢复底部旧版 context status line 与操作提示
- 去掉 `User:` / `Assistant:` 标签，改回 `❯` / `⏺` transcript 标记
- 将工具调用从卡片式面板改回紧凑的行式显示
- 为 assistant 消息恢复 Markdown 渲染
- 修复中文输入法一次提交多个汉字时被拆成单字符的问题
- 恢复 `/` 命令候选菜单、方向键选择、Tab 补全与 Enter 执行
- 调整空会话初始留白，避免 logo 与输入区过于拥挤
- transcript 改为贴底布局，短对话时也保留顶部呼吸感
- 模型默认值改为从 `~/.nocode/config.yaml` 读取并写回

## 设计说明

旧版 TUI 的主要价值不在“功能更多”，而在终端里的信息层级更紧、色彩更克制、结构更像一个长期使用的开发工具。

因此这次没有推翻 Ink 架构，而是做了两层处理：

1. 保留 Ink + Zustand + backend event 的新结构
2. 把旧版的配色、Markdown、宽字符宽度计算、spinner 和 transcript 风格迁回新的组件实现

## 主要实现

### 1. 共享渲染层

新增 `frontend/rendering.ts`，统一承接旧版 TUI 的关键渲染能力：

- ANSI 配色常量
- 宽字符宽度计算
- ANSI-aware wrap / truncate
- Markdown 行级渲染
- spinner 和耗时格式化

### 2. 头部与底部样式回归

调整以下组件：

- `frontend/components/Header.tsx`
- `frontend/components/Composer.tsx`
- `frontend/components/StatusBar.tsx`

恢复旧版：

- 顶部 logo
- 生成中动画
- elapsed time
- 输入区分隔线
- context status line
- 底部快捷键提示

### 3. Transcript 与 Markdown

调整以下组件：

- `frontend/components/Message.tsx`
- `frontend/components/Transcript.tsx`
- `frontend/components/Ansi.tsx`

恢复内容包括：

- assistant Markdown 渲染
- 工具调用紧凑行式布局
- 选中工具高亮
- truecolor ANSI 颜色解析
- system fatal 信息的可读展示

### 4. 中文输入法修复

调整：

- `frontend/components/Composer.tsx`
- `frontend/App.tsx`

将“只接受单字符输入”的逻辑改为“接受任意非控制字符输入”，从而兼容中文输入法一次 commit 多个汉字。

### 5. Slash Command 菜单恢复

新增：

- `frontend/slashCommands.ts`

调整：

- `frontend/components/Composer.tsx`
- `frontend/components/StatusBar.tsx`
- `frontend/App.tsx`

恢复内容包括：

- 输入 `/` 自动弹出命令候选
- `↑/↓` 选择候选
- `Tab` 补全当前命令
- `Enter` 在未精确匹配时先补全，在精确匹配时直接执行
- 命令帮助文案与候选来源统一复用共享定义

### 6. 模型默认值持久化

调整：

- `src/nocode_agent/config/__init__.py`
- `src/nocode_agent/app/backend_stdio.py`
- `frontend/hooks/useBackend.ts`
- `frontend/components/ModelPicker.tsx`

实现改为：

- 启动时优先读取 `~/.nocode/config.yaml` 中的 `default_model`
- 手动切换模型后，把新的 `default_model` 写回 `~/.nocode/config.yaml`
- `--model` 显式启动参数仍然优先于全局默认模型
- model picker 里补充 `current` 标记，并修正 `default` 只显示一次

## 测试

已验证：

```bash
npm --prefix frontend run build

python3 -m unittest \
  tests.test_startup_smoke.LauncherSmokeTest.test_launcher_resolves_real_script_path_when_invoked_via_symlink \
  tests.test_startup_smoke.TuiBackendErrorVisibilityTest.test_tui_shows_backend_stderr_excerpt_and_log_path_on_fatal \
  tests.test_startup_smoke.TuiBackendErrorVisibilityTest.test_tui_prefers_repo_venv_over_stale_python_bin \
  tests.test_startup_smoke.TuiBackendErrorVisibilityTest.test_tui_keeps_terminal_cwd_while_loading_backend_from_repo_source
```

另外做了一轮手工 TTY 冒烟，确认启动后可看到：

- 顶部 logo
- 底部分隔线
- 输入区 `❯`
- context status line
- `/` 输入后即时弹出的命令候选菜单
- `Tab` 补全 `/help`，`Enter` 正常执行
- `~/.nocode/config.yaml` 中的 `default_model` 会影响下次启动

## 后续手工回归建议

建议继续重点手测以下场景：

- 中文输入法连续输入多个汉字并提交
- assistant 输出带标题、列表、代码块、表格的 Markdown
- 生成中 spinner / elapsed time 是否持续刷新
- 工具调用选中、展开、折叠
- slash command 菜单在 `/m`、`/per`、`/res` 等前缀下的筛选和补全行为
- 切换模型后重启 TUI，确认会自动命中上次写入 `~/.nocode/config.yaml` 的默认模型
