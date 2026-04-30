"""Fetch available models from each configured provider's API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from nocode_agent.config import (
    _is_local_base_url,
    normalize_model_base_url,
    resolve_api_key,
)

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 10.0


def detect_provider_type(base_url: str) -> str:
    """Detect provider API type from base_url.

    Returns one of: "openai_compat", "anthropic", "ollama".
    """
    normalized = normalize_model_base_url(base_url)
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()

    if "anthropic.com" in host:
        return "anthropic"
    if _is_local_base_url(normalized):
        return "ollama"
    return "openai_compat"


def _ollama_base_url(base_url: str) -> str:
    """Strip /v1 suffix for Ollama native API calls."""
    normalized = normalize_model_base_url(base_url)
    if normalized.endswith("/v1"):
        return normalized[:-3]
    return normalized


async def fetch_models_for_provider(
    provider_name: str,
    base_url: str,
    api_key: str,
    *,
    proxy: str = "",
    ssl_verify: bool = True,
    timeout: float = _FETCH_TIMEOUT,
) -> list[dict[str, str]]:
    """Fetch model list from a single provider.

    Returns list of {"id": "...", "display_name": "..."}.
    Raises httpx.HTTPError or ValueError on failure.
    """
    normalized = normalize_model_base_url(base_url)
    provider_type = detect_provider_type(normalized)

    client_kwargs: dict[str, Any] = {
        "timeout": timeout,
        "verify": ssl_verify,
    }
    if proxy:
        client_kwargs["proxy"] = proxy

    async with httpx.AsyncClient(**client_kwargs) as client:
        if provider_type == "anthropic":
            url = f"{normalized}/v1/models"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return [
                {"id": m.get("id", ""), "display_name": m.get("display_name") or m.get("id", "")}
                for m in data.get("data", [])
                if m.get("id")
            ]

        if provider_type == "ollama":
            url = f"{_ollama_base_url(normalized)}/api/tags"
            headers: dict[str, str] = {}
            if api_key and api_key != "ollama":
                headers["Authorization"] = f"Bearer {api_key}"
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return [
                {"id": m.get("name", ""), "display_name": m.get("name", "")}
                for m in data.get("models", [])
                if m.get("name")
            ]

        # Default: OpenAI-compatible
        url = f"{normalized}/models"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return [
            {"id": m.get("id", ""), "display_name": m.get("id", "")}
            for m in data.get("data", [])
            if m.get("id")
        ]


async def fetch_all_providers(
    providers_config: dict[str, dict[str, Any]],
    *,
    global_config: dict[str, Any] | None = None,
    timeout: float = _FETCH_TIMEOUT,
) -> dict[str, list[dict[str, str]]]:
    """Fetch model lists from all providers in parallel.

    Returns {provider_name: [{"id", "display_name"}]}.
    Failed providers have an empty list (logged but not raised).
    """
    cfg = global_config or {}

    async def _safe_fetch(name: str, pcfg: dict) -> tuple[str, list[dict[str, str]]]:
        try:
            synthetic = {"base_url": pcfg.get("base_url", ""), "api_key": pcfg.get("api_key", "")}
            api_key = resolve_api_key(synthetic)
            models = await fetch_models_for_provider(
                name,
                pcfg.get("base_url", ""),
                api_key,
                proxy=cfg.get("proxy", ""),
                ssl_verify=cfg.get("ssl_verify", True),
                timeout=timeout,
            )
            return name, models
        except Exception as exc:
            logger.warning("Failed to fetch models from provider '%s': %s", name, exc)
            return name, []

    results = await asyncio.gather(
        *(_safe_fetch(name, pcfg) for name, pcfg in providers_config.items())
    )
    return dict(results)
