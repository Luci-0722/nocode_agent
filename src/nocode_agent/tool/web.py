"""Web 工具。"""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from langchain.tools import tool
from pydantic import BaseModel, Field


class WebSearchInput(BaseModel):
    query: str = Field(description="搜索关键词。")
    max_results: int = Field(default=5, ge=1, le=10, description="最多返回多少条搜索结果。")


def http_get(url: str) -> str:
    """执行带默认请求头的 HTTP GET。"""
    request = Request(
        url,
        headers={
            "User-Agent": "nocode/0.1 (+https://local.workspace)",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8", errors="replace")


def strip_html(text: str) -> str:
    """移除 HTML 标签并压缩空白。"""
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@tool("web_search", args_schema=WebSearchInput)
def web_search(query: str, max_results: int = 5) -> str:
    """执行网页搜索并返回结果摘要。"""
    from nocode_agent.tool.kit import _trim_output, logger

    logger.info("web_search: %s (max=%d)", query, max_results)
    search_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    try:
        html = http_get(search_url)
    except Exception as error:
        return f"错误：网页搜索失败: {error}"

    pattern = re.compile(
        r'(?s)<a[^>]*class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
        r'<a[^>]*class="result__snippet"[^>]*>(?P<snippet>.*?)</a>|'
        r'<a[^>]*class="result__a"[^>]*href="(?P<href2>[^"]+)"[^>]*>(?P<title2>.*?)</a>.*?'
        r'<div[^>]*class="result__snippet"[^>]*>(?P<snippet2>.*?)</div>'
    )

    results: list[str] = []
    for match in pattern.finditer(html):
        href = match.group("href") or match.group("href2")
        title = match.group("title") or match.group("title2")
        snippet = match.group("snippet") or match.group("snippet2") or ""
        if not href or not title:
            continue
        url = urljoin("https://duckduckgo.com", unescape(href))
        clean_title = strip_html(title)
        clean_snippet = strip_html(snippet)
        results.append(f"- {clean_title}\n  URL: {url}\n  摘要: {clean_snippet}")
        if len(results) >= max_results:
            break

    if not results:
        return "未解析到搜索结果。"
    return _trim_output("\n".join(results))


class WebFetchInput(BaseModel):
    url: str = Field(description="要抓取的网页 URL。")
    max_chars: int = Field(default=5000, ge=200, le=20000, description="最多返回多少字符。")


@tool("web_fetch", args_schema=WebFetchInput)
def web_fetch(url: str, max_chars: int = 5000) -> str:
    """抓取网页正文并转成纯文本。"""
    from nocode_agent.tool.kit import _trim_output

    try:
        html = http_get(url)
    except Exception as error:
        return f"错误：网页抓取失败: {error}"

    text = strip_html(html)
    return _trim_output(text[:max_chars])


__all__ = [
    "WebFetchInput",
    "WebSearchInput",
    "http_get",
    "strip_html",
    "web_fetch",
    "web_search",
]
