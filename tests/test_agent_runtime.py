from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import httpx
from langchain_core.messages import AIMessageChunk

from nocode_agent.agent.runtime import MainAgentRuntime, _is_retryable_error


class _FakeCheckpointer:
    async def ensure_setup(self) -> None:
        return None


class _FakeInteractiveBroker:
    async def wait_for_tool_permission(self, request_id: str):
        raise AssertionError(f"unexpected permission request: {request_id}")


class _FakeMainAgent:
    thread_id = "thread-test"


class _FakeStream:
    def __init__(self, items, error: Exception | None = None) -> None:
        self._items = list(items)
        self._error = error
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index < len(self._items):
            item = self._items[self._index]
            self._index += 1
            return item
        if self._error is not None:
            error = self._error
            self._error = None
            raise error
        raise StopAsyncIteration


class _FakeGraphAgent:
    def __init__(self) -> None:
        self.calls = 0

    def astream(self, current_input, config, stream_mode, subgraphs, version):
        self.calls += 1
        if self.calls == 1:
            return _FakeStream([], error=httpx.ReadTimeout("timed out"))
        return _FakeStream(
            [
                {
                    "type": "messages",
                    "ns": (),
                    "data": (
                        AIMessageChunk(content="ok"),
                        {"langgraph_node": "model"},
                    ),
                }
            ]
        )


class RetryableErrorTest(unittest.TestCase):
    def test_httpx_read_timeout_is_retryable(self) -> None:
        self.assertTrue(_is_retryable_error(httpx.ReadTimeout("timed out")))

    def test_wrapped_httpx_read_timeout_is_retryable(self) -> None:
        wrapped = RuntimeError("outer")
        wrapped.__cause__ = httpx.ReadTimeout("timed out")
        self.assertTrue(_is_retryable_error(wrapped))


class MainAgentRuntimeRetryTest(unittest.IsolatedAsyncioTestCase):
    async def test_chat_retries_httpx_read_timeout(self) -> None:
        runtime = MainAgentRuntime(
            agent=_FakeGraphAgent(),
            checkpointer=_FakeCheckpointer(),
            interactive_broker=_FakeInteractiveBroker(),
            main_agent=_FakeMainAgent(),
        )

        with patch("nocode_agent.agent.runtime.asyncio.sleep", new=AsyncMock()) as sleep_mock:
            events = [event async for event in runtime.chat("hello")]

        self.assertEqual(events[0][0], "retry")
        self.assertEqual(events[0][1], "timed out")
        self.assertEqual(events[1], ("text", "ok"))
        sleep_mock.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
