from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from nocode_agent.runtime.paths import PROJECT_CONFIG_PATH, project_config_path

logger = logging.getLogger(__name__)


# 默认配置文件相对项目根路径；实际绝对路径在运行时结合项目根解析。
DEFAULT_CONFIG_PATH = PROJECT_CONFIG_PATH

# 全局兜底配置：当项目目录下没有 .nocode/config.yaml 时，读取 ~/.nocode/config.yaml。
GLOBAL_CONFIG_PATH = Path.home() / ".nocode" / "config.yaml"


def _resolve_default_config_path() -> Path:
    return project_config_path()


def _resolve_global_config_path() -> Path:
    return Path.home() / ".nocode" / "config.yaml"


def _read_yaml_config(config_file: Path) -> dict[str, Any] | None:
    try:
        with open(config_file, encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except FileNotFoundError:
        return None
    except OSError as exc:
        logger.warning("Unable to read config file %s: %s", config_file, exc)
        return None


def _resolve_proxy_section(config: dict[str, Any]) -> tuple[str, Any]:
    """提取代理主配置，兼容字符串和对象两种写法。"""
    proxy_value = config.get("proxy", "")
    if isinstance(proxy_value, dict):
        proxy_url = str(
            proxy_value.get("url")
            or proxy_value.get("value")
            or proxy_value.get("http")
            or ""
        ).strip()
        return proxy_url, proxy_value
    return str(proxy_value or "").strip(), {}


def _split_no_proxy_value(raw_value: Any) -> list[str]:
    """把 no_proxy 输入统一展开为字符串列表。"""
    if raw_value is None:
        return []

    if isinstance(raw_value, str):
        return [item.strip() for item in raw_value.split(",") if item.strip()]

    if isinstance(raw_value, (list, tuple, set)):
        items: list[str] = []
        for item in raw_value:
            items.extend(_split_no_proxy_value(item))
        return items

    return [str(raw_value).strip()] if str(raw_value).strip() else []


def load_config(config_path: str | None = None) -> dict[str, Any]:
    resolved = (
        config_path
        or os.environ.get("NOCODE_AGENT_CONFIG")
        or os.environ.get("NOCODE_CONFIG")
        or str(_resolve_default_config_path())
    )
    config_file = Path(resolved).expanduser()
    global_config_path = _resolve_global_config_path()
    primary = _read_yaml_config(config_file)
    if primary is not None:
        return primary

    # 项目级配置不存在时，回退到全局配置 ~/.nocode/config.yaml
    if config_file != global_config_path:
        logger.debug(
            "Config not found at %s, trying global config at %s",
            config_file, global_config_path,
        )
        fallback = _read_yaml_config(global_config_path)
        if fallback is not None:
            return fallback

    logger.debug("Config file not found: %s", config_file)
    return {}


def load_global_config() -> dict[str, Any]:
    config_file = _resolve_global_config_path()
    config = _read_yaml_config(config_file)
    return config or {}


def save_global_default_model(model_name: str) -> None:
    selected = str(model_name or "").strip()
    if not selected:
        return

    config_file = _resolve_global_config_path()
    payload = load_global_config()
    payload["default_model"] = selected
    try:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)
    except OSError as exc:
        logger.warning("Unable to persist global default model to %s: %s", config_file, exc)


def _is_local_base_url(base_url: str) -> bool:
    """判断模型服务是否指向本机，便于兼容 Ollama 这类本地服务。"""
    raw = normalize_model_base_url(base_url)
    if not raw:
        return False
    host = (urlparse(raw).hostname or "").strip().lower()
    return host in {"localhost", "127.0.0.1", "0.0.0.0"}


def normalize_model_base_url(base_url: str) -> str:
    """把误填的完整接口地址裁剪成客户端需要的基地址。"""
    raw = str(base_url or "").strip().rstrip("/")
    if not raw:
        return ""

    suffixes = (
        "/chat/completions",
        "/responses",
        "/v1/messages",
        "/messages",
    )
    lowered = raw.lower()
    for suffix in suffixes:
        if lowered.endswith(suffix):
            return raw[: -len(suffix)] or raw
    return raw


def _provider_from_base_url(base_url: str) -> str:
    """根据 base_url 推断当前模型供应商。"""
    parsed = urlparse(normalize_model_base_url(base_url))
    host = (parsed.hostname or "").strip().lower()
    path = (parsed.path or "").strip().lower()
    if not host:
        return ""
    if "anthropic.com" in host:
        return "anthropic"
    if "dashscope.aliyuncs.com" in host and (
        "claude-code-proxy" in path or "/apps/anthropic" in path
    ):
        return "anthropic"
    if "dashscope.aliyuncs.com" in host:
        return "dashscope"
    if "bigmodel.cn" in host:
        return "zhipu"
    if "openai.com" in host:
        return "openai"
    return ""


def resolve_model_provider(config: dict[str, Any]) -> str:
    """解析当前配置对应的模型协议供应商。"""
    return _provider_from_base_url(str(config.get("base_url", "") or ""))


def resolve_api_key(config: dict[str, Any]) -> str:
    """统一解析模型 API Key。

    优先读取与当前供应商匹配的专用环境变量。显式配置的 api_key 优先于
    通用 NOCODE_API_KEY，避免启动脚本注入的旧兼容变量覆盖用户当前配置。
    如果目标是本地模型服务且未提供 key，则返回占位值，满足 OpenAI
    兼容客户端的参数要求。
    """
    provider = resolve_model_provider(config)
    primary_env_candidates: list[str] = []
    fallback_env_candidates: list[str] = ["NOCODE_API_KEY"]
    if provider == "anthropic":
        primary_env_candidates.extend(["ANTHROPIC_API_KEY", "DASHSCOPE_API_KEY", "BAILIAN_API_KEY"])
    elif provider == "dashscope":
        primary_env_candidates.extend(["DASHSCOPE_API_KEY", "BAILIAN_API_KEY"])
    elif provider == "zhipu":
        primary_env_candidates.append("ZHIPU_API_KEY")
    elif provider == "openai":
        primary_env_candidates.append("OPENAI_API_KEY")
    else:
        primary_env_candidates.extend(
            [
                "DASHSCOPE_API_KEY",
                "BAILIAN_API_KEY",
                "ANTHROPIC_API_KEY",
                "OPENAI_API_KEY",
                "ZHIPU_API_KEY",
                "OLLAMA_API_KEY",
            ]
        )

    for env_name in primary_env_candidates:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value

    config_value = str(config.get("api_key", "") or "").strip()
    if config_value:
        return config_value

    for env_name in fallback_env_candidates:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value

    if _is_local_base_url(str(config.get("base_url", "") or "")):
        # 本地 Ollama 默认不校验真实密钥，这里给兼容客户端一个占位值。
        return "ollama"

    return ""


def resolve_proxy(config: dict[str, Any]) -> str:
    """统一解析 HTTP 代理地址。

    优先级: 环境变量 NOCODE_PROXY > 配置文件 proxy 字段 > 环境变量 OPENAI_PROXY
    返回空字符串表示不使用代理。
    """
    for env_name in ("NOCODE_PROXY", "OPENAI_PROXY"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value

    config_value, _ = _resolve_proxy_section(config)
    if config_value:
        return config_value

    return ""


def resolve_no_proxy(config: dict[str, Any]) -> list[str]:
    """统一解析不走代理的主机列表。

    优先级: 环境变量 NOCODE_NO_PROXY > 配置文件 no_proxy / proxy.no_proxy > 环境变量 NO_PROXY
    返回空列表表示没有显式绕过规则。
    """
    env_value = os.environ.get("NOCODE_NO_PROXY", "").strip()
    if env_value:
        return _split_no_proxy_value(env_value)

    _, proxy_section = _resolve_proxy_section(config)
    config_value = config.get("no_proxy")
    if config_value is None and isinstance(proxy_section, dict):
        config_value = proxy_section.get("no_proxy")

    resolved = _split_no_proxy_value(config_value)
    if resolved:
        return resolved

    fallback_value = os.environ.get("NO_PROXY", "").strip()
    if fallback_value:
        return _split_no_proxy_value(fallback_value)

    return []


def resolve_request_timeout(config: dict[str, Any], default: float = 90.0) -> float:
    """统一解析模型请求超时时间（秒）。"""
    raw_value = config.get("request_timeout", default)
    try:
        timeout = float(raw_value)
    except (TypeError, ValueError):
        logger.warning("Invalid request_timeout=%r, fallback to %.1f", raw_value, default)
        return default
    if timeout <= 0:
        logger.warning("Non-positive request_timeout=%r, fallback to %.1f", raw_value, default)
        return default
    return timeout


def list_available_models(config: dict[str, Any]) -> list[dict[str, str]]:
    """列出配置中所有可用的模型，返回包含名称和实际 model ID 的列表。

    返回格式: [{"name": "qwen", "model": "glm-5", "is_default": true}, {"name": "qwen/glm-4-flash", "model": "glm-4-flash", "is_default": false}]
    """
    models_section = config.get("models", {})
    if not isinstance(models_section, dict):
        return []

    default_name = str(config.get("default_model", "") or "").strip()
    result: list[dict[str, str]] = []
    for cfg_name, cfg in models_section.items():
        if not isinstance(cfg, dict):
            continue
        default_model_id = cfg.get("model", "")
        if default_model_id:
            result.append({
                "name": cfg_name,
                "model": default_model_id,
                "is_default": "true" if cfg_name == default_name else "false",
            })
        # 添加 variants
        variants = cfg.get("variants", [])
        if isinstance(variants, list):
            for variant_id in variants:
                if variant_id and str(variant_id) != default_model_id:
                    variant_name = f"{cfg_name}/{variant_id}"
                    result.append({
                        "name": variant_name,
                        "model": str(variant_id),
                        "is_default": "true" if variant_name == default_name else "false",
                    })
    return result


def resolve_model_config(config: dict[str, Any], model_name: str | None = None) -> dict[str, Any]:
    """解析指定模型的配置，返回完整的模型参数。

    Args:
        config: 完整配置字典
        model_name: 模型名称（对应 models 段的 key，或 "key/variant_id" 格式）
                    为 None 时使用 default_model

    Returns:
        包含 model, base_url, api_key 等字段的配置字典
    """
    models_section = config.get("models", {})
    if not isinstance(models_section, dict):
        models_section = {}

    target_name = model_name or config.get("default_model")
    if not target_name:
        raise ValueError("No model specified and no default_model configured")

    # 解析名称：可能是 "qwen" 或 "qwen/glm-4-flash"
    parts = target_name.split("/", 1)
    cfg_name = parts[0]
    variant_id = parts[1] if len(parts) > 1 else None

    if cfg_name not in models_section:
        raise ValueError(f"Model config '{cfg_name}' not found in models configuration")

    model_cfg = models_section[cfg_name]
    if not isinstance(model_cfg, dict):
        raise ValueError(f"models.{cfg_name} must be a dict")

    # 确定实际使用的 model ID
    if variant_id:
        actual_model = variant_id
    else:
        actual_model = model_cfg.get("model", "")

    if not actual_model:
        raise ValueError(f"No model ID specified for '{target_name}'")

    return {
        "model": actual_model,
        "base_url": model_cfg.get("base_url", ""),
        "api_key": model_cfg.get("api_key", ""),
    }


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "GLOBAL_CONFIG_PATH",
    "load_config",
    "load_global_config",
    "save_global_default_model",
    "normalize_model_base_url",
    "resolve_api_key",
    "resolve_model_provider",
    "resolve_no_proxy",
    "resolve_proxy",
    "resolve_request_timeout",
    "list_available_models",
    "resolve_model_config",
]
