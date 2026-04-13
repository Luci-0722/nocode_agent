# nocode_agent Agent Notes

这份文档只用于辅助 agent 快速理解仓库、定位代码和规避重复错误。

它不是工作流规范，也不用于约束开发步骤。

这份文档本身需要持续维护，不是一次性说明。

- 项目结构变了，就更新“项目概览”和“目录结构”
- 启动方式、调试命令、测试命令变了，就更新“常用命令”
- 常见实现约定变了，就更新“开发提示”与 “TUI / Terminal 开发提示”
- 反复出现的新坑，持续追加到“开发注意点（持续维护）”

## 源码仓库

**当前工作目录就是 nocode_agent 的源码仓库。**

你正在运行的 nocode_agent 的源码就在这里。用户在此目录启动 nocode，通常意味着要调试或开发 nocode_agent 本身。

关键路径：
- 源码入口：`src/nocode_agent/`
- 运行时路径解析：`src/nocode_agent/runtime/paths.py`

## 项目概览

`nocode_agent` 是一个独立的 NoCode agent 运行时仓库，当前以 Python 后端 + TypeScript TUI 前端的方式组织。

当前主线：

- Python 包代码集中在 `src/nocode_agent/`
- 终端界面入口在 `frontend/tui.ts`
- 启动脚本是根目录 `nocode`
- 默认配置模板是 `config.example.yaml`
- 运行时状态默认写入项目根下的 `.state/`
- subagent 统一从项目 `.nocode/agents/` 和用户 `~/.nocode/agents/` 发现；仓库默认 agent 也已经迁到项目 `.nocode/agents/`

## 目录结构

仓库内最重要的目录如下：

```text
src/nocode_agent/
  agent/          主 agent 构建与运行
  app/            stdio backend / ACP server 入口
  compression/    压缩、auto compact、session memory
  config/         配置读取与解析
  log/            日志初始化
  model/          模型工厂
  persistence/    checkpoint / 线程历史持久化
  prompt/         主提示词与上下文拼装
  runtime/        运行时路径、bootstrap、交互控制
  skills/         skills 发现、注册、恢复
  tool/           内建工具实现
  bundled_skills/ 仓库自带 skills

frontend/
  tui.ts                 TUI 主入口
  input_protocol.ts      原始输入协议解析
  terminal_utils.ts      终端控制、滚轮、剪贴板等工具

.nocode/agents/          项目级 subagent 定义（运行时发现，仓库默认 agent 也放这里）

scripts/
  install_nocode_launcher.sh

tests/
  test_startup_smoke.py
```

## 常用命令

这部分需要随项目实际启动方式、测试方式持续更新，避免命令失效。

安装：

```bash
pip install -e .
```

启动 TUI：

```bash
nocode
```

未安装启动器时：

```bash
node frontend/tui.ts
```

恢复会话：

```bash
nocode --resume
```

最小冒烟测试：

```bash
python3 -m unittest discover -s tests -v
```

单独调试后端：

```bash
PYTHONPATH=src python3 -m nocode_agent.app.backend_stdio
```

## 开发提示

这部分用于沉淀当前实现下仍然有效的开发约定；如果代码结构变化，相关提示也要同步更新。

### 通用提示

- 先看现有实现，再改代码，避免基于猜测补逻辑
- 定位问题、澄清需求、或连续排障失败时，优先用“费曼式外化”的方式沟通：先用 2-4 句简单说明当前认为系统是怎样工作的、判断依据是什么、还有哪些假设未确认、下一步准备如何验证
- 这样做的目标是暴露理解缺口并让用户及时纠偏，不是展示完整思维链；简单任务不要过度解释
- 改动尽量贴近现有架构，减少额外结构债
- 配置、路径、状态目录相关逻辑优先复用 `src/nocode_agent/runtime/paths.py`
- 运行时相对路径应锚定项目根，而不是当前 shell 的 `cwd`
- 涉及配置时，优先参考 `config.example.yaml`
- 敏感信息不要写进仓库
- 自定义 subagent 优先放在 `.nocode/agents/*.md`，frontmatter 最少包含 `name` 和 `description`
- 自定义 subagent 如需限制能力，优先用 `tools` / `disallowedTools`，不要只靠 prompt 约束

### 测试提示

- TUI、启动器、路径解析、后端启动相关改动，优先关注 `tests/test_startup_smoke.py`
- 交互行为改动除了自动测试，通常还需要补一轮手工验证
- 如果改动影响启动流程，重点检查 `.venv`、`NOCODE_PROJECT_DIR`、日志路径、`.state/` 路径

## TUI / Terminal 开发提示

这部分和终端交互实现强相关，前端交互逻辑变化后应同步更新。

这部分是高频踩坑区，改动 `frontend/tui.ts`、`frontend/input_protocol.ts`、`frontend/terminal_utils.ts` 时建议重点关注。

- TUI 开发的时候，注意输入光标要在输入框中
- 改动输入区渲染、换行、滚动、loading spinner、高度计算后，要重新检查光标定位
- 至少注意这些场景：空输入、单行输入、多行输入、中文输入、自动换行、生成中状态
- 输入事件分成 `keypress` 和原始 `data` 两路，处理控制键时不要把转义序列拆坏
- `Escape` 既可能是独立按键，也可能是方向键等序列前缀，相关逻辑改动后要回归方向键和 ESC 行为
- TUI 运行时会启用 raw mode、alt screen、mouse tracking、kitty keyboard protocol；退出时要完整恢复
- 修改鼠标选择、滚轮滚动、复制逻辑后，要检查不会影响正常输入和光标位置
- 如果 backend 启动失败，界面应继续展示 fatal 信息、最近 stderr 摘要和日志文件路径
- 启动 backend 时，源码态优先使用项目目录下的 `.venv`，避免被陈旧的 `PYTHON_BIN` 干扰

## 开发注意点（持续维护）

这一节专门用来沉淀反复出现的开发错误。

后续每次开发，如果发现某个问题容易重复出现，或者已经反复踩坑，可以直接往这里追加。

建议记录格式：

```text
- [模块名] 错误现象：
  正确做法：
  最小验证：
```

当前已知高频注意点：

- [ANSI 序列分片] 错误现象：TUI 显示类似 "186;198;207m" 的残留文本，这是 ANSI 真彩色序列的 RGB 部分被原样输出。
  原因：模型输出中的 ANSI 序列在流式传输时被分片，`\x1b[38;2;186;198;207m` 可能拆成多个 chunk，TUI 的 `stripAnsi` 只能匹配完整序列。
  正确做法：在工具层统一剥离 ANSI 序列（`src/nocode_agent/tool/kit.py` 的 `_strip_ansi`），`_trim_output` 会自动调用；runtime 层的模型输出也会调用。TUI 端作为防御层再处理分片残留（必须含分号才匹配，避免误删 "2.0m" 等正常文本）。
  最小验证：正则 `\x1b\[[0-9;]*[mK]`，TUI 防御用 `[0-9]+;[0-9;]*m`。

- [TUI 输入框] 错误现象：改完 composer、wrap、spinner 或 prompt 前缀后，光标显示到了输入框外，或者落在错误行。
  正确做法：任何影响输入区可视高度、前缀宽度、换行结果的改动，都同步检查 `positionCursor()`、`renderComposer()`、`wrap()` 的一致性。
  最小验证：检查空输入、长文本换行、多行输入、中文宽字符、生成中状态下，光标始终落在输入正文区域。

- [终端退出] 错误现象：TUI 异常退出后，终端还停留在 raw mode、鼠标跟踪没关闭、光标状态异常。
  正确做法：所有退出路径都走统一收尾逻辑，确保关闭 mouse tracking、keyboard protocol、alt screen，并恢复 `stdin` raw mode。
  最小验证：至少看一轮 `Ctrl+C`、正常退出、backend fatal 这几种退出路径。

- [路径解析] 错误现象：相对路径跟着启动目录飘，导致 `.state/`、数据库或日志写到错误位置。
  正确做法：运行时相对路径统一锚定项目根，优先复用 `runtime/paths.py` 的解析逻辑。
  最小验证：从仓库根、子目录、只读目录分别启动，确认状态文件仍落在目标项目根下。

- [启动器项目根] 错误现象：通过软链接或外部 shell 环境启动时，误用了旧的 `NOCODE_PROJECT_DIR`，导致读取了错误仓库或错误配置。
  正确做法：启动器显式把 `NOCODE_PROJECT_DIR` 绑定到当前仓库根，不继承外部残留项目根。
  最小验证：通过 symlink 启动，并预置一个错误的 `NOCODE_PROJECT_DIR`，确认最终仍绑定当前仓库。

- [Python 解释器选择] 错误现象：明明仓库里有 `.venv`，但启动时仍误用外部 `PYTHON_BIN` 或系统 Python，导致依赖缺失或行为不一致。
  正确做法：源码态启动 backend 时优先使用项目根下的 `.venv`，只有本地虚拟环境不存在时才回退到外部解释器。
  最小验证：构造一个错误 `PYTHON_BIN`，确认 TUI 仍优先命中仓库 `.venv` 并正常拉起 backend。

- [Backend 报错可见性] 错误现象：backend 初始化失败时，前端只显示退出，开发者不知道 stderr 和日志位置。
  正确做法：fatal 或异常退出时，TUI 保留错误摘要、最近 stderr 和日志文件路径。
  最小验证：构造一个故意失败的 backend，确认界面能看到 `fatal`、`最近 stderr` 和 `日志文件`。

## 开发流程
 1、开始编码前先与用户确认方案
 2、编码完成后与用户对齐修改内容
 2、用户觉得没问题了，提交commit
