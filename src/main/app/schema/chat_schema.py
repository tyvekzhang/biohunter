from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastlib.stream.schema import BaseMessage, BaseStreamMessage
from pydantic import BaseModel, Field


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
    data: Annotated[ConfirmMessageData, Field(default_factory=ConfirmMessageData)]


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


class ChatMessage(BaseMessage[StreamMessage]):
    user_id: Annotated[int, Field(description="消息所属的用户ID")]
    task_id: Annotated[str, Field(description="消息所属的任务ID")]
    conversation_id: Annotated[int, Field(description="消息所属的对话ID")]
    type: int = Field(
        ..., description="消息类型：1-文件检索，2-单细胞数据", ge=1, le=3, example=1
    )
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
        self.updated_at = datetime.now(UTC)


class ChatRequest(BaseModel):
    """聊天请求数据模型"""

    conversation_id: int = Field(
        ..., description="会话ID，用于标识和关联特定的对话会话", ge=1, example=12345
    )

    content: str = Field(
        ...,
        description="用户输入的文本消息内容",
        min_length=1,
        max_length=4000,
        example="请分析这个基因的细胞表面表达情况",
    )

    type: int = Field(
        ..., description="消息类型：1-文件检索，2-单细胞数据", ge=1, le=3, example=1
    )

    options: dict = Field(
        default_factory=dict,
        description="扩展选项字典，用于传递额外的配置参数",
        example={
            "analysis_depth": "detailed",
            "include_references": True,
            "language": "zh-CN",
        },
    )
