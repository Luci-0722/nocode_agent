"""Persistent stdio backend for the TypeScript TUI frontend."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

from nocode_agent.persistence import (
    estimate_thread_tokens,
    list_threads,
    load_thread_messages,
    resolve_checkpoint_path,
)
from nocode_agent.config import (
    load_global_config,
    parse_model_name,
    resolve_model_config,
    save_global_default_model,
)
from nocode_agent.runtime.bootstrap import (
    configure_runtime_logging,
    create_agent_from_config,
    load_runtime_config,
)
from nocode_agent.app.stdio import configure_stdio_encoding
from nocode_agent.tool.kit import _sanitize_text

logger = logging.getLogger(__name__)

_stream_task: asyncio.Task | None = None
_current_model: str = ""  # "provider/model_id" format
_model_cache: dict[str, list[dict[str, str]]] = {}  # provider_name -> [{"id", "display_name"}]
_cache_populated: bool = False


def _resolve_initial_model_name(config: dict[str, Any]) -> str:
    providers = config.get("providers", {})
    if not isinstance(providers, dict) or not providers:
        raise ValueError("No providers configured")

    candidates: list[tuple[str, str]] = []

    explicit = str(os.environ.get("NOCODE_MODEL_NAME", "") or "").strip()
    if explicit:
        candidates.append(("NOCODE_MODEL_NAME", explicit))

    global_default = str(load_global_config().get("default_model", "") or "").strip()
    if global_default:
        candidates.append(("global_config", global_default))

    project_default = str(config.get("default_model", "") or "").strip()
    if project_default:
        candidates.append(("project_config", project_default))

    for source, candidate in candidates:
        try:
            provider_name, _ = parse_model_name(candidate)
        except ValueError:
            logger.warning("Ignoring invalid %s=%s", source, candidate)
            continue
        if provider_name in providers:
            return candidate
        logger.warning("Ignoring %s=%s: provider '%s' not found", source, candidate, provider_name)

    # Fall back to first provider — model_id will be wrong but agent starts
    first_provider = next(iter(providers))
    return f"{first_provider}/unknown"


async def _build_agent(
    config: dict[str, Any],
    *,
    thread_id: str | None = None,
    model_name: str | None = None,
):
    return await create_agent_from_config(
        config,
        thread_id=thread_id or os.environ.get("NOCODE_THREAD_ID") or None,
        model_name=model_name,
    )


def _emit(event: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(event, ensure_ascii=False) + "\n")
    sys.stdout.flush()


# 缓存最后一次 token_usage 事件的百分比，避免 status 事件硬编码 100 覆盖真实值。
_last_tokens_left_percent: int = 100


def _build_status_event(agent, config: dict[str, Any], event_type: str = "status") -> dict[str, Any]:
    """构建发给 TUI 的状态快照。"""
    context_window = max(1, int(getattr(agent, "context_window", 128_000) or 128_000))
    return {
        "type": event_type,
        "thread_id": agent.thread_id,
        "model": agent.model_name,
        "model_name": _current_model,  # "provider/model_id" qualified name
        "subagent_model": agent.subagent_model_name,
        "reasoning_effort": getattr(agent, "reasoning_effort", ""),
        "cwd": os.getcwd(),
        "context_window": context_window,
        "tokens_left_percent": _last_tokens_left_percent,
    }


async def _stream_prompt(agent, prompt: str, config: dict[str, Any]) -> None:
    global _last_tokens_left_percent
    logger.info("Prompt started: thread=%s, chars=%d", getattr(agent, "thread_id", "-"), len(prompt))
    try:
        async for event_type, *data in agent.chat(prompt):
            if event_type == "runtime_event":
                payload = data[0] if data else {}
                if isinstance(payload, dict):
                    if payload.get("type") == "token_usage":
                        _last_tokens_left_percent = max(
                            0, min(100, payload.get("tokens_left_percent", _last_tokens_left_percent))
                        )
                    _emit(payload)
            elif event_type == "text":
                _emit({"type": "text", "delta": data[0]})
            elif event_type == "retry":
                _emit(
                    {
                        "type": "retry",
                        "message": str(data[0]),
                        "attempt": data[1],
                        "max_retries": data[2],
                        "delay": data[3],
                    }
                )
            elif event_type == "tool_start":
                name = data[0]
                args = data[1] if len(data) > 1 else {}
                tool_call_id = data[2] if len(data) > 2 else ""
                _emit(
                    {
                        "type": "tool_start",
                        "name": name,
                        "args": args,
                        "tool_call_id": tool_call_id,
                    }
                )
                if name == "ask_user_question":
                    qs = args.get("questions", [])
                    logger.info("ask_user_question detected, questions=%s", qs)
                    _emit(
                        {
                            "type": "question",
                            "questions": qs,
                            "tool_call_id": tool_call_id,
                        }
                    )
            elif event_type == "tool_end":
                _emit(
                    {
                        "type": "tool_end",
                        "name": data[0],
                        "output": data[1] if len(data) > 1 else "",
                        "tool_call_id": data[2] if len(data) > 2 else "",
                    }
                )
            elif event_type in {"subagent_start", "subagent_tool_start", "subagent_tool_end", "subagent_finish"}:
                payload = data[0] if data else {}
                if isinstance(payload, dict):
                    _emit(payload)
    except asyncio.CancelledError:
        logger.info("Prompt cancelled: thread=%s", getattr(agent, "thread_id", "-"))
        _emit({"type": "cancelled"})
    except Exception as error:
        logger.error("Stream error: %s", error, exc_info=True)
        _emit({"type": "error", "message": f"stream error: {error}"})
    else:
        logger.info("Prompt finished: thread=%s", getattr(agent, "thread_id", "-"))
    _emit(_build_status_event(agent, config))
    _emit({"type": "done"})


async def _handle_message(agent, payload: dict[str, Any], config: dict[str, Any]) -> tuple[Any, bool]:
    global _current_model, _last_tokens_left_percent, _stream_task
    message_type = payload.get("type")

    if message_type == "clear":
        await agent.clear()
        _emit({"type": "cleared", "thread_id": agent.thread_id})
        return agent, True

    if message_type == "status":
        _emit(_build_status_event(agent, config))
        return agent, True

    if message_type == "fetch_models":
        force_refresh = bool(payload.get("force", False))
        from nocode_agent.model.fetch_models import fetch_models_for_provider
        from nocode_agent.config import resolve_api_key, resolve_proxy, resolve_ssl_verify

        if _cache_populated and not force_refresh:
            _emit({
                "type": "models_fetch_start",
                "providers": list(_model_cache.keys()),
            })
            for pname, models in _model_cache.items():
                _emit({
                    "type": "models_fetch_provider",
                    "result": {
                        "provider_name": pname,
                        "status": "loaded",
                        "models": models,
                        "error": None,
                    },
                })
            _emit({
                "type": "models_fetch_done",
                "cache": _model_cache,
                "current": _current_model,
                "default": config.get("default_model", ""),
            })
            return agent, True

        providers = config.get("providers", {})
        if not isinstance(providers, dict) or not providers:
            _emit({"type": "error", "message": "No providers configured"})
            return agent, True

        provider_names = list(providers.keys())
        _emit({"type": "models_fetch_start", "providers": provider_names})

        proxy = resolve_proxy(config)
        ssl_verify = resolve_ssl_verify(config)

        async def _fetch_one(pname: str, pcfg: dict) -> None:
            try:
                synthetic = {"base_url": pcfg.get("base_url", ""), "api_key": pcfg.get("api_key", "")}
                api_key = resolve_api_key(synthetic)
                models = await fetch_models_for_provider(
                    pname,
                    pcfg.get("base_url", ""),
                    api_key,
                    proxy=proxy,
                    ssl_verify=ssl_verify,
                )
                _model_cache[pname] = models
                _emit({
                    "type": "models_fetch_provider",
                    "result": {
                        "provider_name": pname,
                        "status": "loaded",
                        "models": models,
                        "error": None,
                    },
                })
            except Exception as exc:
                logger.warning("Failed to fetch models for %s: %s", pname, exc)
                _model_cache[pname] = []
                _emit({
                    "type": "models_fetch_provider",
                    "result": {
                        "provider_name": pname,
                        "status": "error",
                        "models": [],
                        "error": str(exc),
                    },
                })

        await asyncio.gather(*(_fetch_one(pn, providers[pn]) for pn in provider_names))
        _cache_populated = True

        _emit({
            "type": "models_fetch_done",
            "cache": _model_cache,
            "current": _current_model,
            "default": config.get("default_model", ""),
        })
        return agent, True

    if message_type == "switch_model":
        target_model = str(payload.get("model", "")).strip()
        if not target_model:
            _emit({"type": "error", "message": "empty model name"})
            return agent, True

        if _stream_task and not _stream_task.done():
            _emit({"type": "error", "message": "cannot switch model while generation is running"})
            return agent, True

        try:
            provider_name, model_id = parse_model_name(target_model)
        except ValueError as error:
            _emit({"type": "error", "message": str(error)})
            return agent, True

        providers = config.get("providers", {})
        if provider_name not in providers:
            _emit({"type": "error", "message": f"Provider '{provider_name}' not found"})
            return agent, True

        # Validate model against cache if available
        cached_models = _model_cache.get(provider_name, [])
        if cached_models:
            cached_ids = [m.get("id", "") for m in cached_models]
            if model_id not in cached_ids:
                _emit({"type": "error", "message": f"Model '{model_id}' not found in provider '{provider_name}'. Available: {', '.join(cached_ids)}"})
                return agent, True

        try:
            model_cfg = resolve_model_config(config, target_model)
            logger.info("Switching model: %s -> %s (%s)", _current_model, target_model, model_cfg.get("model"))
            next_agent = await _build_agent(
                config,
                thread_id=getattr(agent, "thread_id", None),
                model_name=target_model,
            )
            _current_model = target_model
            save_global_default_model(target_model)
            _emit({"type": "model_switched", "model_name": target_model, "model": model_cfg.get("model")})
            _emit(_build_status_event(next_agent, config))
            return next_agent, True
        except ValueError as error:
            _emit({"type": "error", "message": str(error)})
            return agent, True

    if message_type == "list_threads":
        db_path = resolve_checkpoint_path(config)
        source_filter = str(payload.get("source", "")).strip() or "tui"
        threads = list_threads(db_path, source=source_filter)
        _emit({"type": "thread_list", "threads": threads})
        return agent, True

    if message_type == "resume_thread":
        target_thread = str(payload.get("thread_id", "")).strip()
        if not target_thread:
            _emit({"type": "error", "message": "empty thread_id for resume"})
            return agent, True
        agent._thread_id = target_thread
        db_path = resolve_checkpoint_path(config)
        context_window = max(1, int(getattr(agent, "context_window", 128_000) or 128_000))
        estimated = estimate_thread_tokens(db_path, target_thread)
        tokens_left = max(0, context_window - estimated)
        tokens_left_percent = max(0, min(100, round(tokens_left * 100 / context_window)))
        _last_tokens_left_percent = tokens_left_percent
        _emit(_build_status_event(agent, config, event_type="resumed"))
        return agent, True

    if message_type == "load_history":
        db_path = resolve_checkpoint_path(config)
        messages = load_thread_messages(db_path, thread_id=agent.thread_id)
        _emit({"type": "history", "messages": messages})
        return agent, True

    if message_type == "exit":
        return agent, False

    _emit({"type": "error", "message": f"unknown message type: {message_type}"})
    return agent, True


async def main() -> int:
    global _stream_task, _current_model
    configure_stdio_encoding()
    try:
        config = load_runtime_config()
        configure_runtime_logging(config)
        _current_model = _resolve_initial_model_name(config)
        agent = await _build_agent(config, model_name=_current_model or None)
        if _current_model:
            save_global_default_model(_current_model)
    except Exception as error:
        configure_runtime_logging()
        logger.error("Fatal error during initialization: %s", error)
        _emit({"type": "fatal", "message": str(error)})
        return 1

    _emit(_build_status_event(agent, config, event_type="hello"))
    while True:
        line = await asyncio.to_thread(sys.stdin.readline)
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            logger.warning("Invalid JSON on stdin: %s", error)
            _emit({"type": "error", "message": f"invalid json: {error}"})
            continue

        message_type = payload.get("type")

        if message_type == "prompt":
            prompt = _sanitize_text(str(payload.get("text", "")).strip())
            if not prompt:
                _emit({"type": "error", "message": "empty prompt"})
                continue
            if _stream_task and not _stream_task.done():
                logger.info("Prompt queued: thread=%s, chars=%d", agent.thread_id, len(prompt))
                await agent.enqueue_user_input(prompt)
                _emit({"type": "prompt_queued", "text": prompt})
            else:
                _stream_task = asyncio.create_task(_stream_prompt(agent, prompt, config))
            continue

        if message_type == "question_answer":
            answer = _sanitize_text(str(payload.get("text", "")).strip())
            if not answer:
                _emit({"type": "error", "message": "empty question answer"})
                continue
            try:
                await agent.submit_question_answer(answer)
            except RuntimeError as error:
                _emit({"type": "error", "message": str(error)})
            continue

        if message_type == "permission_decision":
            request_id = str(payload.get("request_id", "")).strip()
            decisions = payload.get("decisions", [])
            if not isinstance(decisions, list) or not decisions:
                _emit({"type": "error", "message": "empty permission decisions"})
                continue
            try:
                await agent.submit_tool_permission_decision(request_id, decisions)
            except RuntimeError as error:
                _emit({"type": "error", "message": str(error)})
            continue

        if message_type == "cancel":
            if _stream_task and not _stream_task.done():
                _stream_task.cancel()
            else:
                _emit({"type": "status", "message": "idle"})
            continue

        agent, should_continue = await _handle_message(agent, payload, config)
        if not should_continue:
            break

    if _stream_task and not _stream_task.done():
        _stream_task.cancel()
        try:
            await _stream_task
        except asyncio.CancelledError:
            pass
    return 0


def run() -> None:
    """同步启动入口，供 console script 与 `python -m` 调用。"""
    raise SystemExit(asyncio.run(main()))


__all__ = [
    "main",
    "run",
]


if __name__ == "__main__":
    run()
