# TUI Glyph Profile

## 背景

TUI 的视觉符号如果直接依赖终端字体，会导致 macOS 和 Windows 显示不一致。

此前的 Windows fallback 能规避乱码和错位，但会让 Windows 与 macOS 进入两套视觉语言。现在默认策略改为跨平台一致：所有平台默认使用同一套保守、稳定的 portable glyph。

## 本次调整

- 新增 `TUI_GLYPH_PROFILE`
- 默认 profile 为 `portable`，macOS / Windows / Linux 都使用同一套 ASCII 友好的符号
- `NOCODE_TUI_GLYPHS=rich` 时启用原来的 Unicode-rich 符号
- 回答前缀、用户前缀、工具 headline、工具树、subagent 树、输入区、生成 spinner、启动动画统一从 `UI_GLYPHS` 读取
- Markdown 标题、引用、列表、表格和分隔线也使用同一 profile，避免回答内容里继续散落平台相关符号

## 结果

- macOS 和 Windows 默认显示一致
- 默认 UI 不再依赖高风险 Unicode 字形
- 想保留 rich Unicode 观感时，可以通过环境变量显式开启

## 验证

- `npm --prefix frontend run build`
