# 项目配置固定为 `.nocode/config.yaml`

## 背景

此前默认配置解析会沿着当前工作目录向上查找 `config.yaml`。

这会和业务项目自己的根目录配置撞车。只要用户在某个项目里启动 `nocode`，运行时就可能把那个项目本身的 `config.yaml` 误当成 nocode 配置。

## 本次调整

默认配置查找改为：

1. 显式环境变量 `NOCODE_AGENT_CONFIG` / `NOCODE_CONFIG`
2. 项目目录下的 `.nocode/config.yaml`
3. 全局配置 `~/.nocode/config.yaml`

同时做了两件事：

- 默认路径改成运行时动态解析，避免模块导入时把某一刻的 cwd 锁成默认配置路径
- 项目根只认祖先目录里的 `.nocode/config.yaml`，不再把根目录 `config.yaml` 当成项目标记
- 运行时配置读取改成“全局配置为基底，项目配置覆盖合并”，避免为了项目级配置或本地授权目录自动创建 `.nocode/config.yaml` 后，意外把全局模型配置遮住

## 结果

- 业务项目自己的 `config.yaml` 不会再被 nocode 默认读取
- 在项目子目录启动时，只要祖先目录存在 `.nocode/config.yaml`，仍然会正确绑定到项目根
- 如果没有项目级配置，会继续回退到 `~/.nocode/config.yaml`
- 如果项目级 `.nocode/config.yaml` 只写了局部字段，其余字段仍会继承全局 `~/.nocode/config.yaml`

## 验证

已补回归测试，覆盖：

- 子目录启动时解析祖先 `.nocode/config.yaml`
- 忽略项目根旧式 `config.yaml`
- 项目级配置缺失时回退全局 `~/.nocode/config.yaml`
- 全局配置与项目 `.nocode/config.yaml` 的覆盖合并
- 启动链路按默认 `.nocode/config.yaml` 拉起 backend
