# SPDX-License-Identifier: MIT
import asyncio
import logging
from typing import AsyncGenerator, Literal, Sequence

import httpx
from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    TextMessage,
    ThoughtEvent,
)
from autogen_core import CancellationToken
from fastmcp import Client
from fastmcp.client.logging import LogMessage
from fastlib.cache.manager import get_cache_client

from .team_agent import BaseTeamAgent
from .assistant_team import AssistantTeam, ConclusionEvent
from .mcp_workbench import FastMCPWorkbench
from .context import get_current_message
from .schema import Message

Conversation = ""
ConversationResponse = None

from .llm_client import model_client

logger = logging.getLogger(__name__)


class ThoughtChunkEvent(ModelClientStreamingChunkEvent):
    type: Literal["ThoughtChunkEvent"] = "ThoughtChunkEvent"


class MessageChunkEvent(ModelClientStreamingChunkEvent):
    type: Literal["MessageChunkEvent"] = "MessageChunkEvent"


class AssistantTeamAgent(BaseTeamAgent[AssistantTeam]):
    async def on_messages_stream(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        last_message: BaseChatMessage | None = None
        async for message in self._team.run_stream(
            task=messages,
            cancellation_token=cancellation_token,
        ):
            if isinstance(message, TaskResult):
                assert last_message is not None
                yield Response(
                    chat_message=last_message,
                    inner_messages=message.messages,
                )
            elif isinstance(message, ModelClientStreamingChunkEvent):
                if message.source == self._team.task_agent.name:
                    yield ThoughtChunkEvent(
                        source=self._name,
                        models_usage=message.models_usage,
                        content=message.content,
                        metadata=message.metadata,
                    )
                elif message.source == self._team.summary_agent.name:
                    yield MessageChunkEvent(
                        source=self._name,
                        models_usage=message.models_usage,
                        content=message.content,
                        metadata=message.metadata,
                    )
            elif isinstance(message, BaseChatMessage):
                last_message = message
                if message.source == "user":
                    yield message
                elif message.source == self._team.task_agent.name:
                    yield ThoughtEvent(
                        source=self._name,
                        models_usage=message.models_usage,
                        content=message.to_text(),
                        metadata=message.metadata,
                    )
                elif message.source == self._team.summary_agent.name:
                    message = message.model_copy()
                    message.source = self._name
                    yield message
            else:
                yield message


class Assistant:
    def __init__(self, task_id: str):
        mcp = None

        self.task_id = task_id

        self.queue: asyncio.Queue[
            BaseAgentEvent | BaseChatMessage | Response
        ] = asyncio.Queue()

        self.mcp_client = Client(mcp, log_handler=self._mcp_client_log_handler)
        self.workbench = FastMCPWorkbench(self.mcp_client)
        self.agent = AssistantTeamAgent(
            name="assistant",
            description="a helpful assistant",
            team=AssistantTeam(
                model_client=model_client,
                workbench=self.workbench,
            ),
        )
        self.cancellation_token = None

        assistant_storages.store_sync(task_id, self)

    async def _run_stream(
        self, task: str | BaseChatMessage | Sequence[BaseChatMessage]
    ):
        self.cancellation_token = CancellationToken()
        try:
            async for message in self.agent.run_stream(
                task=task, cancellation_token=self.cancellation_token
            ):
                await self.queue.put(message)
        finally:
            self.cancellation_token = None

    @classmethod
    def cancel(cls, task_id: str):
        assistant = assistant_storages.get_sync(task_id)
        if assistant is None:
            return
        if assistant.cancellation_token is not None:
            assistant.cancellation_token.cancel()

    @classmethod
    async def run_stream(
        cls, task_id: str, task: str | BaseChatMessage | Sequence[BaseChatMessage]
    ) -> AsyncGenerator[
        BaseAgentEvent | BaseChatMessage | Response, None
    ]:
        ctx = None
        logger.debug(f"Handle task({task_id}): {task}")

        input_messages: list[BaseChatMessage] = []

        if isinstance(task, str):
            message = TextMessage(source="user", content=task)
            input_messages.append(message)
        elif isinstance(task, BaseChatMessage):
            input_messages.append(task)

        assistant = assistant_storages.get_sync(task_id)
        if assistant is None:
            assistant = cls(task_id)
            logger.info(f"Assistant for {task_id} is created")

            # get the conversation history and append to the input messages
            message = get_current_message()
            conversation = await get_conversation(message)
            if conversation:
                input_messages[:0] = [
                    TextMessage(source=message.role, content=message.content)
                    for message in conversation.messages
                    if message.content is not None and message.role != "system"
                ]

        logger.info(f"Assistant for {task_id} start to run")

        # get the file list and append to the input messages
        files = await ctx.files
        file_list_str = "\n".join([f"- {name}" for name in files])
        input_messages.append(
            TextMessage(
                source="assistant",
                content=f"I notice that there are some files in the workspace, here is the list:\n{file_list_str}",
            )
        )

        conclusion = None
        try:
            async with assistant.mcp_client:
                _task = asyncio.create_task(assistant._run_stream(input_messages))
                while not _task.done():
                    message = await assistant.queue.get()
                    if isinstance(message, ConclusionEvent):
                        conclusion = message.conclusion
                    yield message
                await _task
        finally:
            logger.info(f"Assistant for {task_id} conclude {conclusion}")
            if conclusion != "NEED_USER_INPUT":
                await assistant_storages.delete(task_id)
                logger.info(f"Assistant for {task_id} is deleted")


async def get_conversation(message: Message) -> Conversation | None:
    url = f""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer ",
                "X-User-Id": message.user_id,
            },
        )
        if response.status_code != 200:
            logger.error(
                f"Failed to get conversation history: {response.status_code} {response.text}"
            )
            return None
        result = ConversationResponse.model_validate_json(response.content)
        if result.code != 0:
            logger.error(f"Failed to get conversation history: {result.message}")
            return None
        return result.data
    
assistant_storages = get_cache_client()
