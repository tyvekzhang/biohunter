from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class FenceContent(BaseModel):
    pass


class Fence(BaseModel):

    tag: str
    content: list[FenceContent] | FenceContent

    def to_text(self) -> str:
        if isinstance(self.content, list):
            content = ",".join(
                [
                    content.model_dump_json(indent=0, serialize_as_any=True)
                    for content in self.content
                ]
            )
            content = f"[\n{content}\n]"
        else:
            content = self.content.model_dump_json(indent=0, serialize_as_any=True)
        return f"""
```{self.tag}
{content}
```
"""


class ChatAgentTaskFence(Fence):
    tag: Literal["chat-agent-task"] = "chat-agent-task"


class HandlerParam(BaseModel):
    pass


class ChatAgentTaskFenceContent(FenceContent):
    type: Annotated[
        Literal["search", "file", "method", "code", "mcp"],
        Field(description="渲染的图标类型"),
    ]
    label: Annotated[
        str,
        Field(description="渲染的文本信息, 由各个Agent/任务根据自身功能及调用状态返回"),
    ]
    status: Annotated[
        Literal["running", "success", "failed"],
        Field(description="Agent任务执行的状态"),
    ]
    hoverable: Annotated[
        bool | None,
        Field(description="是否可点击, 即点击后是否展示右侧抽屉或其他响应方式"),
    ] = None
    handler: Annotated[
        Literal["webSearch", "mcpTool"] | None,
        Field(description="hoverable为true时有意义, 点击消息时的响应handler"),
    ] = None
    handlerParam: Annotated[
        HandlerParam | None,
        Field("hoverable为true时有意义, 响应点击时传入上面约定的响应handler函数的参数"),
    ] = None


class MCPToolHandlerParam(HandlerParam):
    name: Annotated[str, Field(description="工具名称")]
    description: Annotated[str, Field(description="工具描述/说明")]
    output: Annotated[
        Any,
        Field(description="工具输出, 用于展示在右侧抽屉里的json数据"),
    ]


class MCPToolCallFenceContent(ChatAgentTaskFenceContent):
    type: Literal["mcp"] = "mcp"
    label: str = "Tool call running..."
    status: Literal["running"] = "running"
    hoverable: bool = True
    handler: Literal["mcpTool"] = "mcpTool"
    handlerParam: MCPToolHandlerParam


class MCPToolResultFenceContent(ChatAgentTaskFenceContent):
    type: Literal["mcp"] = "mcp"
    label: str = "Tool call completed"
    status: Literal["success"] = "success"
    hoverable: bool = True
    handler: Literal["mcpTool"] = "mcpTool"
    handlerParam: MCPToolHandlerParam


class MCPToolFailedFenceContent(ChatAgentTaskFenceContent):
    type: Literal["mcp"] = "mcp"
    label: str = "Tool call failed"
    status: Literal["failed"] = "failed"
    hoverable: bool = True
    handler: Literal["mcpTool"] = "mcpTool"
    handlerParam: MCPToolHandlerParam


class ChatFileFenceContent(FenceContent):
    fileName: str
    format: str
    fileSize: int
    path: str
    fileId: int


class ChatFlieListFence(Fence):
    tag: Literal["chat-filelist-view"] = "chat-filelist-view"
    content: list[ChatFileFenceContent]
