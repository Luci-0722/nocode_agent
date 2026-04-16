# 项目级额外工作区目录授权

## 背景

此前 nocode 的文件访问根只有当前 shell 的 `cwd`。

这意味着：

- `read/write/edit/list_dir/glob/grep` 只能访问 `cwd` 内的路径
- `bash` 即使开启了系统沙箱，也只对白名单里的当前工作目录放行
- 想访问 `cwd` 外的目录时，没有项目级持久化授权机制

## 本次实现

新增了“额外工作区目录”能力，但不改变原始 `cwd` 语义：

- `cwd` 仍然是默认工作区根
- 额外允许访问的目录统一存到项目 `.nocode/config.yaml`
- 配置字段为 `workspace.additional_directories`

示例：

```yaml
workspace:
  additional_directories:
    - /abs/path/to/shared-data
    - /abs/path/to/another-repo
```

## 授权流程

当模型调用以下工具并命中未授权目录时：

- `read`
- `write`
- `edit`
- `list_dir`
- `glob`
- `grep`
- `bash`

运行时会通过现有 TUI `permission_request` 流程弹出审批。

用户批准后会立即：

1. 把目录写入当前项目 `.nocode/config.yaml`
2. 刷新当前会话的有效工作区根集合
3. 继续执行原始工具调用

下次重新打开同一项目时，不需要再次授权。

## 层级关系

运行时的有效配置改为：

1. 全局 `~/.nocode/config.yaml` 作为基底
2. 项目 `.nocode/config.yaml` 作为覆盖层

这样即使项目配置只为了持久化 `workspace.additional_directories`，也不会遮住用户全局模型配置。

额外目录的有效根集合为：

- 当前 `cwd`
- 全局 `workspace.additional_directories`
- 项目 `workspace.additional_directories`

`security.deny_paths` 仍然优先级更高，命中的路径不会因为额外目录授权而放行。

## 工具与沙箱

以下组件已统一切到同一套授权根集合：

- 文件工具路径校验
- `glob` / `list_dir` / `grep` 的可见性过滤
- `bash` 的系统沙箱白名单

这样不会出现“文件工具能访问、bash 还被沙箱挡住”的不一致。

## 当前取舍

- 额外目录审批写回项目 `.nocode/config.yaml` 时，当前实现使用 `PyYAML` 重写文件；已有注释和手工排版不会保留
- `bash` 的额外目录识别基于常见路径 token 的启发式解析，优先覆盖绝对路径、`~`、`../` 等明显越界场景

## 验证

已补测试覆盖：

- 全局配置与项目配置的覆盖合并
- 项目配置里的 `workspace.additional_directories` 放行 `cwd` 外路径
- 批准额外目录访问后，把目录写回项目 `.nocode/config.yaml`
- 现有路径/启动链路回归测试全部通过
