# SPDX-License-Identifier: MIT
"""
Assistant Team Module for Coordinated AI Task Execution
"""

import re
from typing import Literal

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.messages import (
    BaseAgentEvent,
    HandoffMessage,
    ModelClientStreamingChunkEvent,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
)
from autogen_agentchat.teams import Swarm
from autogen_core.models import ChatCompletionClient
from autogen_core.tools import Workbench

# Import prompts from separate file
from . import prompts

# Agent Names
PLANNING_AGENT_NAME = "planning_agent"
TASK_AGENT_NAME = "task_agent"
SUMMARY_AGENT_NAME = "summary_agent"


class ConclusionEvent(BaseAgentEvent):
    """
    Event indicating the final conclusion of a task execution.
    """

    type: Literal["ConclusionEvent"] = "ConclusionEvent"
    conclusion: Literal["COMPLETED", "FAILED", "NEED_USER_INPUT"]

    def to_text(self) -> str:
        """Convert conclusion to human-readable text."""
        return f"The task is {self.conclusion}."


class AssistantTeam(Swarm):
    """
    A coordinated team of AI assistants for task execution and summarization.

    Comprises three specialized agents that work together:
    - Planning Agent: Breaks down the task into executable steps.
    - Task Agent: Executes analysis and computation tasks using tools.
    - Summary Agent: Provides final summaries and conclusions.
    """

    def __init__(
        self,
        model_client: ChatCompletionClient,
        workbench: Workbench,
        model_client_stream=True,
        planning_agent_prompt: str = prompts.DEFAULT_PLANNING_PROMPT,
        task_agent_prompt: str = prompts.DEFAULT_TASK_PROMPT,
        summary_agent_prompt: str = prompts.DEFAULT_SUMMARY_PROMPT,
    ):
        """
        Initialize the assistant team.

        Args:
            model_client: Chat completion client for agent communication
            workbench: Tool workbench for task execution
            model_client_stream: Enable streaming responses
            planning_agent_prompt: System prompt for the planning agent
            task_agent_prompt: System prompt for the task agent
            summary_agent_prompt: System prompt for the summary agent
        """
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        # --- Planning Agent ---
        self.planning_agent = AssistantAgent(
            PLANNING_AGENT_NAME,
            model_client=model_client,
            handoffs=[TASK_AGENT_NAME], 
            system_message=planning_agent_prompt,
            model_client_stream=model_client_stream,
            reflect_on_tool_use=False,
        )

        # --- Task Execution Agent ---
        task_model_client = ChatCompletionClient.load_component(
            model_client.dump_component()
        )
        if isinstance(task_model_client, OpenAIChatCompletionClient):
            task_model_client._create_args["temperature"] = 0.0

        self.task_agent = AssistantAgent(
            TASK_AGENT_NAME,
            model_client=task_model_client,
            workbench=workbench,
            # Task Agent 可以将任务转回 Planning Agent 重新规划，或交给 Summary Agent 总结
            handoffs=[PLANNING_AGENT_NAME, SUMMARY_AGENT_NAME],
            system_message=task_agent_prompt,
            model_client_stream=model_client_stream,
            reflect_on_tool_use=False,
        )

        # --- Summary Agent ---
        self.summary_agent = AssistantAgent(
            SUMMARY_AGENT_NAME,
            model_client=model_client,
            system_message=summary_agent_prompt,
            model_client_stream=model_client_stream,
        )

        # Initialize swarm with termination condition
        super().__init__(
            participants=[
                self.planning_agent,
                self.task_agent,
                self.summary_agent,
            ],
            termination_condition=SourceMatchTermination(SUMMARY_AGENT_NAME),
            initiator=self.planning_agent,
        )

    async def run_stream(self, *, task, cancellation_token=None):
        """
        Execute task with real-time streaming and conclusion detection.
        """
        self.conclusion: str | None = None
        conclusion_message = ""

        async for message in super().run_stream(
            task=task,
            cancellation_token=cancellation_token,
            initiator=self.planning_agent,
        ):
            # Process streaming chunks for conclusion detection
            if isinstance(message, ModelClientStreamingChunkEvent):
                if message.source == self.summary_agent.name and not self.conclusion:
                    conclusion_message += message.content
                    if "\n" in conclusion_message or " " in conclusion_message:
                        left, right = re.split(r"[\n\s]+", conclusion_message, 1)
                        self.conclusion = left.strip()
                        if right:
                            message.content = right
                        else:
                            continue
                    else:
                        continue

                # Add metadata for logging context
                if message.source == self.planning_agent.name:
                    message.metadata = {"logger_name": "planning"}
                elif message.source == self.task_agent.name:
                    message.metadata = {"logger_name": "execution_reasoning"}
                elif message.source == self.summary_agent.name:
                    message.metadata = {"logger_name": "content"}

            # Filter internal team coordination messages
            if isinstance(message, (HandoffMessage, ToolCallSummaryMessage)):
                continue
            if (
                isinstance(message, (ToolCallRequestEvent, ToolCallExecutionEvent))
                and message.content[0].name.startswith(f"transfer_to_")
            ):
                continue

            yield message

        # Emit final conclusion event
        if self.conclusion:
            if "NEED_USER_INPUT" in self.conclusion:
                self.conclusion = "NEED_USER_INPUT"
            elif "COMPLETED" in self.conclusion:
                self.conclusion = "COMPLETED"
            else:
                self.conclusion = "FAILED"
            yield ConclusionEvent(
                source=self.summary_agent.name,
                conclusion=self.conclusion,
            )
        else:
            yield ConclusionEvent(
                source=self.summary_agent.name,
                conclusion="FAILED",
            )