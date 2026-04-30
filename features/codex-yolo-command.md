# codex --yolo command

## 背景

仓库内 bundled skill `long-task-execution` 的示例命令仍使用 `codex exec`。

## 改动

- 将示例更新为 `codex --yolo exec`，使文档示例与新的命令前缀约定一致。

## 影响范围

- 仅影响帮助文本示例，不改变脚本参数解析或运行时逻辑。

## 最小验证

- 运行 `bash src/nocode_agent/bundled_skills/long-task-execution/scripts/ralph_loop.sh --help`
- 确认 Examples 段显示 `codex --yolo exec`
