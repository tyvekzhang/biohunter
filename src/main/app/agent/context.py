# SPDX-License-Identifier: MIT
from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

from src.main.app.schema.chat_schema import ChatMessage

_current_message: ContextVar[ChatMessage | None] = ContextVar(
    "current_message", default=None
)


@contextmanager
def set_current_message(message: ChatMessage) -> Generator[ChatMessage, None, None]:
    token = _current_message.set(message)
    try:
        yield message
    finally:
        _current_message.reset(token)


def get_current_message() -> ChatMessage:
    message = _current_message.get()
    if message is None:
        raise RuntimeError("No active message found.")
    return message
