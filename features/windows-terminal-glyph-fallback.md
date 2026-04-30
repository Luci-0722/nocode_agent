# Windows 终端符号降级

## 背景

Windows 终端即使已经切到 UTF-8，也不代表所有符号都能和 macOS 终端一致显示。

像 `⏺`、`❯`、`⎿`、`↳`、Braille spinner、盒绘字符这类装饰符号，在部分 Windows Terminal / PowerShell / CMD 字体组合下会出现宽度错位、显示成异常字符，或者让回答前缀看起来不正常。

## 本次调整

- 前端渲染层新增按平台分流的 `UI_GLYPHS`
- `win32` 下把回答前缀、用户前缀、工具详情树、subagent 树统一降级为 ASCII
- 生成中的 spinner 在 Windows 下改为 `| / - \\`
- 启动 bootstrap 动画在 Windows 下改用 ASCII 轨道和边框，不再依赖盒绘和特殊几何字符

## 结果

- Windows 下 agent 回答前面的符号和工具树更稳定
- 启动动画和生成状态不再依赖高风险字形
- macOS / 非 Windows 终端继续保留原本的视觉符号

## 验证

- `npm --prefix frontend run build`
