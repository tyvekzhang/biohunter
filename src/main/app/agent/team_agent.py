from typing import Any, AsyncGenerator, Generic, Mapping, Sequence, TypeVar

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    TextMessage,
    ThoughtEvent,
)
from autogen_agentchat.state import BaseState
from autogen_agentchat.teams import BaseGroupChat
from autogen_core import CancellationToken, ComponentModel
from pydantic.main import BaseModel
from typing_extensions import Self


class TeamAgentState(BaseState):
    team_state: Any


class TeamAgentConfig(BaseModel):
    name: str
    description: str
    team: ComponentModel


T = TypeVar("T", bound=BaseGroupChat)


class BaseTeamAgent(BaseChatAgent, Generic[T]):

    def __init__(
        self,
        name: str,
        description: str,
        team: T,
    ):
        super().__init__(name=name, description=description)
        self._team = team

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        message_types: set[type[BaseChatMessage]] = set()
        for agent in self._team._participants:
            message_types.update(agent.produced_message_types)
        return tuple(message_types)

    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        result: Response | None = None
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                result = message
        assert result is not None
        return result

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
            elif isinstance(message, BaseChatMessage):
                last_message = message
                if message.source == "user":
                    yield message
                else:
                    yield ThoughtEvent(
                        source=message.source,
                        models_usage=message.models_usage,
                        content=message.to_text(),
                        metadata=message.metadata,
                    )
            else:
                yield message

    async def run(
        self,
        *,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> TaskResult:
        """Run the agent with the given task and return the result."""
        if cancellation_token is None:
            cancellation_token = CancellationToken()
        input_messages: list[BaseChatMessage] = []
        output_messages: list[BaseAgentEvent | BaseChatMessage] = []
        if task is None:
            pass
        elif isinstance(task, str):
            text_msg = TextMessage(content=task, source="user")
            input_messages.append(text_msg)
            # output_messages.append(text_msg)
        elif isinstance(task, BaseChatMessage):
            input_messages.append(task)
            # output_messages.append(task)
        else:
            if not task:
                raise ValueError("Task list cannot be empty.")
            # Task is a sequence of messages.
            for msg in task:
                if isinstance(msg, BaseChatMessage):
                    input_messages.append(msg)
                    # output_messages.append(msg)
                else:
                    raise ValueError(f"Invalid message type in sequence: {type(msg)}")
        response = await self.on_messages(input_messages, cancellation_token)
        if response.inner_messages is not None:
            output_messages += response.inner_messages
        output_messages.append(response.chat_message)
        return TaskResult(messages=output_messages)

    async def run_stream(
        self,
        *,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        """Run the agent with the given task and return a stream of messages
        and the final task result as the last item in the stream."""
        if cancellation_token is None:
            cancellation_token = CancellationToken()
        input_messages: list[BaseChatMessage] = []
        output_messages: list[BaseAgentEvent | BaseChatMessage] = []
        if task is None:
            pass
        elif isinstance(task, str):
            text_msg = TextMessage(content=task, source="user")
            input_messages.append(text_msg)
            # output_messages.append(text_msg)
            # yield text_msg
        elif isinstance(task, BaseChatMessage):
            input_messages.append(task)
            # output_messages.append(task)
            # yield task
        else:
            if not task:
                raise ValueError("Task list cannot be empty.")
            for msg in task:
                if isinstance(msg, BaseChatMessage):
                    input_messages.append(msg)
                    # output_messages.append(msg)
                    # yield msg
                else:
                    raise ValueError(f"Invalid message type in sequence: {type(msg)}")
        async for message in self.on_messages_stream(
            input_messages, cancellation_token
        ):
            if isinstance(message, Response):
                # yield message.chat_message
                # output_messages.append(message.chat_message)
                yield TaskResult(messages=output_messages)
            else:
                yield message
                if isinstance(message, ModelClientStreamingChunkEvent):
                    # Skip the model client streaming chunk events.
                    continue
                output_messages.append(message)

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        await self._team.reset()

    async def on_pause(self, cancellation_token: CancellationToken) -> None:
        await self._team.pause()

    async def on_resume(self, cancellation_token: CancellationToken) -> None:
        await self._team.pause()

    async def save_state(self) -> Mapping[str, Any]:
        team_state = await self._team.save_state()
        return TeamAgentState(team_state=team_state).model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        team_agent_state = TeamAgentState.model_validate(state)
        await self._team.load_state(team_agent_state.team_state)

    def _to_config(self) -> BaseModel:
        return TeamAgentConfig(
            name=self.name,
            description=self.description,
            team=self._team.dump_component(),
        )

    @classmethod
    def _from_config(cls, config: TeamAgentConfig) -> Self:
        return cls(
            name=config.name,
            description=config.description,
            team=BaseGroupChat.load_component(config.team),
        )
