"""运行中用户输入与提问等待的交互桥接。"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime


class InteractiveSessionBroker:
    """管理运行中追加输入和提问等待。"""

    def __init__(self) -> None:
        self._pending_inputs: list[str] = []
        self._input_lock = asyncio.Lock()
        self._question_future: asyncio.Future[str] | None = None
        self._question_lock = asyncio.Lock()
        self._permission_future: asyncio.Future[dict[str, Any]] | None = None
        self._permission_lock = asyncio.Lock()
        self._permission_request_id = ""

    async def enqueue_user_input(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        async with self._input_lock:
            self._pending_inputs.append(cleaned)

    async def drain_user_inputs(self) -> list[str]:
        async with self._input_lock:
            drained = list(self._pending_inputs)
            self._pending_inputs.clear()
            return drained

    async def ask_user_question(self, questions: list[dict[str, Any]]) -> str:
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        async with self._question_lock:
            if self._question_future is not None and not self._question_future.done():
                raise RuntimeError("当前已有待回答的问题，请先等待用户完成回答。")
            self._question_future = future

        try:
            return await future
        finally:
            async with self._question_lock:
                if self._question_future is future:
                    self._question_future = None

    async def submit_question_answer(self, answer: str) -> None:
        async with self._question_lock:
            future = self._question_future
            if future is None or future.done():
                raise RuntimeError("当前没有待回答的问题。")
            future.set_result(answer)

    async def wait_for_tool_permission(
        self,
        request_id: str,
    ) -> dict[str, Any]:
        """等待前端提交工具审批结果。"""
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        async with self._permission_lock:
            if self._permission_future is not None and not self._permission_future.done():
                raise RuntimeError("当前已有待处理的工具审批请求，请先完成审批。")
            self._permission_future = future
            self._permission_request_id = request_id

        try:
            return await future
        finally:
            async with self._permission_lock:
                if self._permission_future is future:
                    self._permission_future = None
                    self._permission_request_id = ""

    async def submit_tool_permission_decision(
        self,
        request_id: str,
        decisions: list[dict[str, Any]],
    ) -> None:
        """提交工具审批结果，用于恢复 LangGraph interrupt。"""
        async with self._permission_lock:
            future = self._permission_future
            if future is None or future.done():
                raise RuntimeError("当前没有待处理的工具审批请求。")
            if request_id and request_id != self._permission_request_id:
                raise RuntimeError("工具审批请求 ID 不匹配，请刷新当前审批界面后重试。")
            future.set_result({"decisions": decisions})


class PendingUserInputMiddleware(AgentMiddleware):
    """在每次模型调用前注入运行中追加的用户消息。"""

    name = "pending_user_input"

    def __init__(self, broker: InteractiveSessionBroker) -> None:
        self._broker = broker

    async def abefore_model(self, state: dict[str, Any], runtime: Runtime[Any]) -> dict[str, Any] | None:
        texts = await self._broker.drain_user_inputs()
        if not texts:
            return None
        runtime.stream_writer(
            {
                "type": "queued_prompt_injected",
                "texts": texts,
            }
        )
        return {
            "messages": [
                {"role": "user", "content": text}
                for text in texts
            ]
        }


__all__ = [
    "InteractiveSessionBroker",
    "PendingUserInputMiddleware",
]
