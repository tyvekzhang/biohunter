# SPDX-License-Identifier: MIT
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generator

from src.main.app.schema.chat_schema import TestMessage

_current_message: ContextVar[TestMessage | None] = ContextVar(
    "current_message", default=None
)


@contextmanager
def set_current_message(message: TestMessage) -> Generator[TestMessage, None, None]:
    token = _current_message.set(message)
    try:
        yield message
    finally:
        _current_message.reset(token)


def get_current_message() -> TestMessage:
    message = _current_message.get()
    if message is None:
        raise RuntimeError("No active message found.")
    return message
