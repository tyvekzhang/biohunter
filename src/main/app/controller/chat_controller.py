# SPDX-License-Identifier: MIT
"""Chat relate controller"""

import asyncio
from fastapi import APIRouter
from fastlib.stream.sse import EventSourceResponse
from fastlib.stream.handler import AsyncStreamHandler
from fastlib.cache import get_cache_client
from loguru import logger
from src.main.app.agent.assistant import Assistant
from src.main.app.agent.context import set_current_message
from src.main.app.schema.chat_schema import Message
from autogen_agentchat.messages import (
    TextMessage,
)

chat_router = APIRouter()


async def new_chat(message: Message = None, query: str = None):
    # task = TextMessage(content=query, source="user")

    # with set_current_message(message):
    #     async for event in Assistant.run_stream(message.task_id, task):
    #         if hasattr(event, "content") and not event.content:
    #             logger.warning(
    #                 f"Skipping event with empty content: {type(event)}"
    #             )
    #             continue
    #         logger.info(event)
    yield {"hello": "world"}
    await asyncio.sleep(1)


@chat_router.get("/chat")
async def chat():
    message_id = "message_id"
    message = Message(
        id=message_id,
        user_id="user_id",
        task_id="task_id",
        conversation_id="conversation_id",
    )
    source = new_chat(message, "")

    handler_storage = await get_cache_client()

    await handler_storage.set(message_id, message)

    handler = AsyncStreamHandler[Message](
        message,
        source,
        handler_storage,
        buffer_size=0,
    )
    await handler.start()

    return EventSourceResponse(handler.get_content_stream())
