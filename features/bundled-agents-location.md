# 内置 Subagent 改为包内发布

## 背景

此前仓库把 nocode 自带的 subagent 定义直接放在项目 [`.nocode/agents`](/Users/lucheng/Projects/nocode_agent/.nocode/agents)。

这会把“内置默认值”和“项目自定义覆盖”混在一起，语义不清，也让打包发布和版本排查变得别扭。

## 本次调整

- 内置 subagent 迁移到 `src/nocode_agent/bundled_agents/`
- agent 发现顺序调整为 `builtin -> user -> project`
- `.nocode/agents/` 只保留项目级自定义或覆盖定义
- `pyproject.toml` 补充 `bundled_agents/*.md` 的 package data

## 结果

- 内置 agent 跟随 nocode 版本一起发布
- 用户和项目仍然可以用同名 agent 覆盖内置默认定义
- 项目目录里的 `.nocode/agents/` 不再承担“内置资源目录”的职责

## 验证

- 补充了 subagent registry 测试，确认 builtin agent 会被注册
- 补充了 project override builtin 的回归测试
- 保留 user/project 覆盖顺序不变
