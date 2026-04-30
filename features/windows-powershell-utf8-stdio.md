## Windows PowerShell UTF-8 Stdio

### 背景

Windows PowerShell 默认控制台编码常常是 GBK。`nocode_agent` 的 Python backend 以前直接把 `ensure_ascii=False` 的 JSON 事件和日志写到标准流，遇到 emoji、扩展 Unicode 或部分中日韩字符时，可能抛出 `UnicodeEncodeError`，前端最终显示：

```text
stream error: 'gbk' codec cannot encode character ...
```

### 变更

- 在 `src/nocode_agent/app/stdio.py` 新增 `configure_stdio_encoding()`
- backend 启动时优先把 `stdin`、`stdout`、`stderr` 重配置为 UTF-8
- 重配置使用 `errors="replace"`，避免宿主环境不完全支持时再次因编码异常中断
- 新增 `tests/test_startup_smoke.py` 单测覆盖 stdio 重配置逻辑

### 影响

- Windows PowerShell / CMD 下的 TUI 流式输出对 Unicode 更稳健
- backend 错误日志与 JSON 事件编码行为一致
- 不改变前端协议，也不影响非 Windows 环境

### 验证

```bash
python3 -m unittest tests.test_startup_smoke.BackendStdioEncodingTest -v
```
