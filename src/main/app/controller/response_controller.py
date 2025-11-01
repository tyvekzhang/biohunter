# SPDX-License-Identifier: MIT
"""Chat relate controller"""

from datetime import datetime
from fastapi import APIRouter
from fastlib.stream.sse import EventSourceResponse
from fastlib.stream.handler import AsyncStreamHandler
from fastlib.cache import get_cache_client
from fastlib.logging import logger
from src.main.app.agent.assistant import Assistant
from src.main.app.agent.context import set_current_message
from src.main.app.schema.chat_schema import TestMessage
from autogen_agentchat.messages import (
    TextMessage,
)

response_router = APIRouter()


async def new_chat(message: TestMessage = None, query: str = None):
    task = TextMessage(content=query, source="user")
    
    with set_current_message(message):
        async for event in Assistant.run_stream(message.task_id, task):
            if hasattr(event, "content") and not event.content:
                logger.warning(
                    f"Skipping event with empty content: {type(event)}"
                )
                continue
            yield event

@response_router.post("/responses")
async def create_response(query: str):
    message_id = "message_id"
    message = TestMessage(
        id=message_id,
        user_id="user_id",
        task_id="task_id",
        conversation_id="conversation_id",
    )
    source = new_chat(message, query)


    handler_storage = await get_cache_client()

    await handler_storage.set(message_id, message.model_dump_json())

    handler = AsyncStreamHandler[TestMessage](
        message,
        source,
        handler_storage,
        buffer_size=0,
    )
    await handler.start()

    return EventSourceResponse(handler.get_content_stream())
