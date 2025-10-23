# SPDX-License-Identifier: MIT
"""
Schema module for AI agent communication
"""

from datetime import datetime
from typing import Annotated, Iterable, Literal

from fastlib.stream.schema import BaseMessage, BaseStreamMessage
from pydantic import BaseModel, Field


class StreamMessage(BaseStreamMessage):
    """Base stream message with event type."""
    event: Literal["success", "confirm", "done", "error"]


class StreamMessageData(BaseModel):
    """Stream message data with status code and content."""
    code: int
    message: str | None
    thinking: str | None = None


class SuccessMessageData(StreamMessageData):
    """Success message data with content."""
    code: Literal[200] = 200
    message: str
    thinking: None = None


class SuccessThinkingData(StreamMessageData):
    """Success thinking data with reasoning content."""
    code: Literal[200] = 200
    message: None = None
    thinking: str


class SuccessMessage(StreamMessage):
    """Success event message."""
    event: Literal["success"] = "success"
    data: SuccessMessageData | SuccessThinkingData


class ConfirmMessageData(StreamMessageData):
    """Confirmation message data."""
    code: Literal[203] = 203
    message: str = ""
    thinking: None = None


class ConfirmMessage(StreamMessage):
    """Confirmation event message."""
    event: Literal["confirm"] = "confirm"
    data: Annotated[ConfirmMessageData, Field(default_factory=ConfirmMessageData)]


class DoneMessageData(StreamMessageData):
    """Completion message data."""
    code: Literal[201] = 201
    message: str = ""
    thinking: None = None


class DoneMessage(StreamMessage):
    """Completion event message."""
    event: Literal["done"] = "done"
    data: Annotated[DoneMessageData, Field(default_factory=DoneMessageData)]


class ErrorMessageData(StreamMessageData):
    """Error message data."""
    code: Literal[501] = 501
    message: str = ""
    thinking: None = None


class ErrorMessage(StreamMessage):
    """Error event message."""
    event: Literal["error"] = "error"
    data: Annotated[ErrorMessageData, Field(default_factory=ErrorMessageData)]


class Message(BaseMessage[StreamMessage]):
    """Main message model for conversation tracking."""
    user_id: Annotated[str, Field(description="User ID for the message")]
    task_id: Annotated[str, Field(description="Task ID for the message")]
    conversation_id: Annotated[str, Field(description="Conversation ID for the message")]
    content: Annotated[
        str,
        Field(
            description="Message content passed to LLM as context",
        ),
    ] = ""
    thought: Annotated[
        str,
        Field(
            description="Agent reasoning process for logging and display, not passed to LLM",
        ),
    ] = ""

    async def append_chunks(self, chunks: Iterable[StreamMessage]) -> None:
        """Append stream chunks to message content and thoughts."""
        for chunk in chunks:
            if isinstance(chunk, SuccessMessage):
                if isinstance(chunk.data, SuccessMessageData):
                    self.content += chunk.data.message
                elif isinstance(chunk.data, SuccessThinkingData):
                    self.thought += chunk.data.thinking
            elif isinstance(chunk, ConfirmMessage):
                self.content += chunk.data.message
            elif isinstance(chunk, DoneMessage):
                self.content += chunk.data.message
            elif isinstance(chunk, ErrorMessage):
                self.content += chunk.data.message
        self.updated_at = datetime.utcnow()