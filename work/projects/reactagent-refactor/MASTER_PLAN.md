# 总体计划

## 总目标

把当前仓库重构为围绕最小 `reactagent` 的独立工程。

本轮既定目标已经完成：

- 真实运行时代码全部收口到 `src/nocode_agent/`
- 根目录兼容 shim 与过渡包已删除
- 运行入口统一为 `nocode_agent.*`
- 已补正式 `pyproject.toml`

## 当前目录形态

当前有效结构：

```text
repo/
  src/
    nocode_agent/
      app/
      agent/
      runtime/
      model/
      prompt/
      tool/
      skills/
      bundled_skills/
      compression/
      persistence/
      config/
      log/
  frontend/
    tui.ts
```

## 阶段划分

### P0 独立运行引导层

状态：已完成

### P1 包结构稳定化

状态：已完成

### P2 ReactAgent 运行时拆分

状态：已完成

### P3 Prompt / Middleware / Tool / Skill 边界化

状态：已完成

### P4 接入层收口

状态：已完成

### P5 删除兼容层并完成最终收口

状态：已完成

交付结果：

- 删除 `nocode_agent.__path__` 桥接
- 删除 `nocode_agent.compression` 对根目录的回落逻辑
- 删除根目录 shim 与旧入口
- `skills`、`compression`、`bundled_skills` 全部迁入包内

### P6 补分发与安装入口

状态：已完成

交付结果：

- 新增 `pyproject.toml`
- 默认路径解析兼容源码仓库与已安装环境

### P7 切换到 src 布局

状态：已完成

交付结果：

- 真实包目录迁移到 `src/nocode_agent/`
- `pyproject.toml` 改为从 `src/` 打包
- `frontend/tui.ts` 在源码态 Python 回退启动时注入 `PYTHONPATH=src`
- 仓库根解析与 bundled `rg` 查找已适配新目录层级

### P8 压缩包根散落模块

状态：已完成

交付结果：

- 入口模块收口到 `src/nocode_agent/app/`
- 路径 / 交互 / HITL / 文件状态模块收口到 `src/nocode_agent/runtime/`
- `tool/` 与 `prompt/` 直接成为正式聚合入口
- 包根只保留标准包入口文件

### P9 移除通用 CLI 入口

状态：已完成

交付结果：

- 已删除 `src/nocode_agent/app/cli.py`
- 已删除 `src/nocode_agent/__main__.py`
- 已移除 `pyproject.toml` 中的 console script 入口
- 当前用户启动方式统一为 TUI

## 后续可选方向

这部分不再属于“兼容迁移”计划，而是新的工程化阶段：

1. 集成测试
2. 发布流程
3. 最小自动化测试基线

## 当前策略

兼容式迁移阶段已经结束。

后续如果继续开发，应直接围绕 `src/nocode_agent/` 真实结构演进，不再增加新的根目录 shim，也不要恢复 `__path__` 桥接。
