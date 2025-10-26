from datetime import datetime, timezone
from typing import Annotated, Iterable, Literal

from pydantic import BaseModel, Field
from fastlib.stream.schema import BaseStreamMessage, BaseMessage


class StreamMessage(BaseStreamMessage):
    event: Literal["success", "confirm", "done", "error"]


class StreamMessageData(BaseModel):
    code: int
    message: str | None
    thinking: str | None = None


class SuccessMessageData(StreamMessageData):
    code: Literal[200] = 200
    message: str
    thinking: None = None


class SuccessThinkingData(StreamMessageData):
    code: Literal[200] = 200
    message: None = None
    thinking: str


class SuccessMessage(StreamMessage):
    event: Literal["success"] = "success"
    data: SuccessMessageData | SuccessThinkingData


class ConfirmMessageData(StreamMessageData):
    code: Literal[203] = 203
    message: str = ""
    thinking: None = None


class ConfirmMessage(StreamMessage):
    event: Literal["confirm"] = "confirm"
    data: Annotated[
        ConfirmMessageData, Field(default_factory=ConfirmMessageData)
    ]


class DoneMessageData(StreamMessageData):
    code: Literal[201] = 201
    message: str = ""
    thinking: None = None


class DoneMessage(StreamMessage):
    event: Literal["done"] = "done"
    data: Annotated[DoneMessageData, Field(default_factory=DoneMessageData)]


class ErrorMessageData(StreamMessageData):
    code: Literal[501] = 501
    message: str = ""
    thinking: None = None


class ErrorMessage(StreamMessage):
    event: Literal["error"] = "error"
    data: Annotated[ErrorMessageData, Field(default_factory=ErrorMessageData)]


class Message(BaseMessage[StreamMessage]):
    user_id: Annotated[str, Field(description="消息所属的用户ID")]
    task_id: Annotated[str, Field(description="消息所属的任务ID")]
    conversation_id: Annotated[
        str, Field(description="消息所属的对话ID")
    ]
    content: Annotated[
        str,
        Field(
            description="消息内容, 会传递给LLM作为上下文",
        ),
    ] = ""
    thought: Annotated[
        str,
        Field(
            description="思考及行动过程, 仅用于记录和展示Agent的思考及行动, 不会传递给LLM作为上下文",
        ),
    ] = ""

    async def append_chunks(self, chunks: Iterable[StreamMessage]) -> None:
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
        self.updated_at = datetime.now(timezone.utc)
