"""交互型工具。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, Field

_TODO_STORE: list[str] = []


class AskUserQuestionInput(BaseModel):
    questions: list[dict] = Field(
        description=(
            "要问用户的问题列表。每个问题是一个 dict，包含："
            "question(必填，问题文本)、header(可选，短标签如 'Auth method')、"
            "options(可选，2-4个选项的list，每个选项有 label 和 description)、"
            "multiSelect(可选，bool，是否可多选)。"
        )
    )


def validate_ask_user_questions(questions: list[dict]) -> list[dict] | str:
    """验证结构化提问载荷。"""
    if not questions:
        return "错误：问题列表不能为空。"

    validated: list[dict] = []
    for index, question in enumerate(questions):
        if not isinstance(question, dict) or not question.get("question"):
            return f"错误：第 {index + 1} 个问题缺少必填的 'question' 字段。"
        entry: dict[str, Any] = {"question": str(question["question"])}
        if question.get("header"):
            entry["header"] = str(question["header"])[:12]
        if isinstance(question.get("options"), list) and question["options"]:
            options = []
            for option in question["options"][:4]:
                if isinstance(option, dict) and option.get("label"):
                    options.append(
                        {
                            "label": str(option["label"]),
                            "description": str(option.get("description", "")),
                        }
                    )
                elif isinstance(option, str):
                    options.append({"label": option, "description": ""})
            if len(options) >= 2:
                entry["options"] = options
        if isinstance(question.get("multiSelect"), bool):
            entry["multiSelect"] = question["multiSelect"]
        validated.append(entry)
    return validated


def make_ask_user_question_tool(
    wait_for_answer: Callable[[list[dict[str, Any]]], Awaitable[str]],
):
    """按会话 broker 构造 ask_user_question 工具。"""

    @tool("ask_user_question", args_schema=AskUserQuestionInput)
    async def ask_user_question(questions: list[dict]) -> str:
        """向用户提出结构化问题以澄清需求或选择方案。"""
        validated = validate_ask_user_questions(questions)
        if isinstance(validated, str):
            return validated
        try:
            answer = await wait_for_answer(validated)
        except RuntimeError as error:
            return f"错误：{error}"
        return answer.strip() or "(跳过了所有问题)"

    return ask_user_question


class TodoItem(BaseModel):
    content: str = Field(description="待办事项内容。")
    status: str = Field(default="pending", description="状态：pending、in_progress 或 completed。")


class TodoInput(BaseModel):
    todos: list[TodoItem] = Field(description="待办事项列表。")


@tool("todo_write", args_schema=TodoInput)
def todo_write(todos: list[TodoItem]) -> str:
    """更新当前会话的待办事项。"""
    global _TODO_STORE
    _TODO_STORE = [
        {"content": item.content.strip(), "status": item.status}
        for item in todos
        if item.content.strip()
    ]
    if not _TODO_STORE:
        return "待办列表已清空。"
    lines = ["待办列表已更新："]
    for item in _TODO_STORE:
        status_mark = {"pending": "□", "in_progress": "◐", "completed": "■"}.get(
            item["status"], "□"
        )
        lines.append(f"- {status_mark} {item['content']}")
    return "\n".join(lines)


@tool("todo_read")
def todo_read() -> str:
    """读取当前会话的待办事项。"""
    if not _TODO_STORE:
        return "当前没有待办事项。"
    lines = []
    for item in _TODO_STORE:
        status_mark = {"pending": "□", "in_progress": "◐", "completed": "■"}.get(
            item["status"], "□"
        )
        lines.append(f"- {status_mark} {item['content']}")
    return "\n".join(lines)


__all__ = [
    "AskUserQuestionInput",
    "TodoInput",
    "TodoItem",
    "make_ask_user_question_tool",
    "todo_read",
    "todo_write",
    "validate_ask_user_questions",
]
