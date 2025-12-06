# SPDX-License-Identifier: MIT
"""Chat relate controller"""

import json
import uuid
from autogen_agentchat.messages import (
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
)
from fastapi import APIRouter
from fastlib.cache import get_cache_client
from fastlib.stream.handler import AsyncStreamHandler
from fastlib.stream.sse import EventSourceResponse
from fastlib.contextvars import get_current_user

from src.main.app.agent.assistant import Assistant, MessageChunkEvent, ThoughtChunkEvent
from src.main.app.agent.assistant_team import ConclusionEvent
from src.main.app.agent.context import set_current_message
from src.main.app.model.message_model import MessageModel
from src.main.app.schema.chat_response import (
    ChatAgentTaskFence,
    MCPToolCallFenceContent,
    MCPToolFailedFenceContent,
    MCPToolHandlerParam,
    MCPToolResultFenceContent,
)
from src.main.app.schema.chat_schema import (
    ChatRequest,
    ChatMessage,
    ConfirmMessage,
    DoneMessage,
    ErrorMessage,
    SuccessMessage,
    SuccessMessageData,
    SuccessThinkingData,
)
from src.main.app.schema.message_schema import RoleInfo
from src.main.app.service.impl.message_service_impl import MessageServiceImpl
from src.main.app.service.message_service import MessageService
from src.main.app.mapper.message_mapper import messageMapper

message_service: MessageService = MessageServiceImpl(mapper=messageMapper)

chat_router = APIRouter()


async def new_chat(message: ChatMessage = None, query: str = None):

    with set_current_message(message):
        async for event in Assistant.run_stream(message.task_id, query):
            if isinstance(event, ThoughtChunkEvent):
                yield SuccessMessage(
                    data=SuccessThinkingData(thinking=event.to_text()),
                )
            elif isinstance(event, MessageChunkEvent):
                yield SuccessMessage(
                    data=SuccessMessageData(message=event.to_text()),
                )
            elif isinstance(event, ToolCallRequestEvent):
                for tool_call in event.content:
                    fence = ChatAgentTaskFence(
                        content=MCPToolCallFenceContent(
                            label=f"Tool {tool_call.name} executing ...",
                            handlerParam=MCPToolHandlerParam(
                                name=tool_call.name,
                                description="",
                                output=json.loads(tool_call.arguments),
                            ),
                        ),
                    )
                    yield SuccessMessage(
                        data=SuccessThinkingData(thinking=fence.to_text()),
                    )
            elif isinstance(event, ToolCallExecutionEvent):
                for tool_call in event.content:
                    if tool_call.is_error:
                        fence = ChatAgentTaskFence(
                            content=MCPToolFailedFenceContent(
                                label=f"Tool {tool_call.name} execution failed",
                                handlerParam=MCPToolHandlerParam(
                                    name=tool_call.name,
                                    description="",
                                    output=tool_call.content,
                                ),
                            ),
                        )
                    else:
                        fence = ChatAgentTaskFence(
                            content=MCPToolResultFenceContent(
                                label=f"Tool {tool_call.name} execution completed",
                                handlerParam=MCPToolHandlerParam(
                                    name=tool_call.name,
                                    description="",
                                    output=tool_call.content,
                                ),
                            ),
                        )
                    yield SuccessMessage(
                        data=SuccessThinkingData(thinking=fence.to_text()),
                    )
            elif isinstance(event, ConclusionEvent):
                conclusion = event.conclusion
    if conclusion == "COMPLETED":
        yield DoneMessage()
    elif conclusion == "NEED_USER_INPUT":
        yield ConfirmMessage()
    else:
        yield ErrorMessage()


@chat_router.post("/responses")
async def create_response(cr: ChatRequest):
    message = ChatMessage(
        id=str(uuid.uuid4()),
        type=cr.type,
        user_id=get_current_user(),
        task_id=str(uuid.uuid4()),
        conversation_id=cr.conversation_id,
    )

    message_data = MessageModel(
        conversation_id=cr.conversation_id, role=RoleInfo.USER, content=cr.content
    )
    await message_service.save(message_data)

    source = new_chat(message, cr.content)

    handler_storage = await get_cache_client()

    handler = AsyncStreamHandler[ChatMessage](
        message,
        source,
        handler_storage,
        buffer_size=0,
    )
    await handler.start()

    return EventSourceResponse(handler.get_content_stream())
