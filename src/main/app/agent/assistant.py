# SPDX-License-Identifier: MIT
import asyncio
from typing import AsyncGenerator, Literal, Sequence

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

from src.main.app.agent.storage import MemoryStorage

from .team_agent import BaseTeamAgent
from .assistant_team import AssistantTeam, ConclusionEvent
from ..mcps.mcp_workbench import FastMCPWorkbench
from .context import get_current_message
from fastlib.logging.handlers import logger
from .llm_client import model_client


class ThoughtChunkEvent(ModelClientStreamingChunkEvent):
    """Event for streaming thought chunks from the task agent."""

    type: Literal["ThoughtChunkEvent"] = "ThoughtChunkEvent"


class MessageChunkEvent(ModelClientStreamingChunkEvent):
    """Event for streaming message chunks from the summary agent."""

    type: Literal["MessageChunkEvent"] = "MessageChunkEvent"


class AssistantTeamAgent(BaseTeamAgent[AssistantTeam]):
    """Agent that handles streaming messages and events from an AssistantTeam."""

    async def on_messages_stream(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        """Stream messages and events from the team, transforming them as needed."""
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
    """Main assistant class that coordinates team agents and MCP tools."""

    def __init__(self, task_id: str):
        """Initialize assistant with task ID and setup components."""
        
        from src.main.app.mcps.mcp_server import mcp

        self.task_id = task_id
        self.queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | Response] = (
            asyncio.Queue()
        )
        self.mcp_client = Client(mcp)
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
        """Internal method to run the agent stream and populate the queue."""
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
        """Cancel a running assistant task."""
        assistant = assistant_storages.get_sync(task_id)
        if assistant is None:
            return
        if assistant.cancellation_token is not None:
            assistant.cancellation_token.cancel()

    @classmethod
    async def run_stream(
        cls, task_id: str, task: str | BaseChatMessage | Sequence[BaseChatMessage]
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        """Run the assistant stream for a given task and yield events/messages."""
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
            conversation = None
            if conversation:
                input_messages[:0] = [
                    TextMessage(source=message.role, content=message.content)
                    for message in conversation.messages
                    if message.content is not None and message.role != "system"
                ]

        logger.info(f"Assistant for {task_id} start to run")

        # get the file list and append to the input messages

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


assistant_storages = MemoryStorage[Assistant]()
