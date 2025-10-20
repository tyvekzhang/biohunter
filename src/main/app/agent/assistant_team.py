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

TASK_AGENT_NAME = "task_agent"
SUMMARY_AGENT_NAME = "summary_agent"

DEFAULT_TASK_PROMPT = """You are a powerful assistant that can use tools to execute tasks. Your role is to:

1. Understand the user's request and break it down into actionable steps
2. Use available tools to complete each step
3. Monitor the execution results and handle any errors
4. If you encounter a situation where you are unsure or need user input, hand off to the summary_agent for guidance
5. You MUST Hand off to the summary_agent when:
    - You want user give you more information to complete the task
    - All tasks are completed successfully


When handing off to the summary_agent, just use the handoff message format to transfer control and don't include anything else.

Remember to:
- Be thorough in your task execution
- Handle errors gracefully
- Keep track of your progress
- Provide clear explanations of your actions
- Use tools efficiently and effectively
- Always share your reasoning before taking action
- Reply in user's language
- Do not engage in conversation with the user
- Defer to the summary_agent for any decisions
- You don't need to summarize the results"""

DEFAULT_SUMMARY_PROMPT = """You are the team spokesperson responsible for summarizing task execution results. Your role is to:

1. Review the conversation history and task execution results
2. Identify the key actions taken and their outcomes
3. Highlight any important findings or insights
4. Note any errors or issues encountered
5. Provide a clear and concise summary of what was accomplished

When summarizing:
- first give a conclusion of the task, one of the following:
  - "COMPLETED" if the task is completed successfully
  - "FAILED" if the task is failed
  - "NEED_USER_INPUT" if you need user input to complete the task
- Do not mention your identity
- Use first-person perspective (e.g., "I have completed...", "I found that...")
- Be factual and objective in your summary
- If there were any problems or incomplete tasks, make sure to mention them
- Focus on the actual results rather than the process
- Present yourself as the unified voice of the team
- Use user's language"""


class ConclusionEvent(BaseAgentEvent):
    type: Literal["ConclusionEvent"] = "ConclusionEvent"
    conclusion: Literal["COMPLETED", "FAILED", "NEED_USER_INPUT"]

    def to_text(self) -> str:
        return f"The task is {self.conclusion}."


class AssistantTeam(Swarm):
    """A team of AI assistants that work together to complete tasks and provide summaries.

    The team consists of two specialized agents:
    1. Task Agent: Executes the main tasks using available tools and makes decisions about task progression
    2. Summary Agent: Reviews the task execution results and provides clear summaries

    The team follows a structured workflow:
    - Task Agent handles the primary task execution and tool usage
    - When tasks are complete or no further progress can be made, control is handed to the Summary Agent
    - Summary Agent provides a comprehensive overview of the results

    Key features:
    - Coordinated task execution and summarization
    - Clear handoff protocol between agents
    - Structured communication and result tracking
    - Error handling and progress monitoring
    """

    def __init__(
        self,
        model_client: ChatCompletionClient,
        workbench: Workbench,
        model_client_stream=True,
        task_agent_prompt=DEFAULT_TASK_PROMPT,
        summary_agent_prompt=DEFAULT_SUMMARY_PROMPT,
    ):
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        task_model_client = ChatCompletionClient.load_component(
            model_client.dump_component()
        )
        if isinstance(task_model_client, OpenAIChatCompletionClient):
            task_model_client._create_args["temperature"] = 0.0

        self.task_agent = AssistantAgent(
            TASK_AGENT_NAME,
            model_client=task_model_client,
            workbench=workbench,
            handoffs=[
                SUMMARY_AGENT_NAME
            ],  # TODO: 自定义handoff工具以隐藏handoff相关的调用事件
            system_message=task_agent_prompt,
            model_client_stream=model_client_stream,
            reflect_on_tool_use=False,
        )
        self.summary_agent = AssistantAgent(
            SUMMARY_AGENT_NAME,
            model_client=model_client,
            system_message=summary_agent_prompt,
            model_client_stream=model_client_stream,
        )
        super().__init__(
            participants=[self.task_agent, self.summary_agent],
            termination_condition=SourceMatchTermination(SUMMARY_AGENT_NAME),
        )

    async def run_stream(self, *, task, cancellation_token=None):
        self.conclusion: str | None = None
        conclusion_message = ""
        async for message in super().run_stream(
            task=task,
            cancellation_token=cancellation_token,
        ):
            if isinstance(message, ModelClientStreamingChunkEvent):
                # 拦截summary_agent的结论输出
                if message.source == self.summary_agent.name:
                    if not self.conclusion:
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
                # 向消息中注入元数据用于MCP上下文日志
                if message.source == self.task_agent.name:
                    message.metadata = {"logger_name": "reasoning"}
                elif message.source == self.summary_agent.name:
                    message.metadata = {"logger_name": "content"}
            # 拦截一些消息使得团队表现的类似一个Agent
            if isinstance(message, HandoffMessage):
                # 拦截团队内的Handoff消息
                continue
            if isinstance(message, ToolCallSummaryMessage):
                # 拦截Tool Call Summary
                continue
            if (
                isinstance(message, (ToolCallRequestEvent, ToolCallExecutionEvent))
                and message.content[0].name == f"transfer_to_{SUMMARY_AGENT_NAME}"
            ):
                # 拦截团队内的Handoff相关Tool Call
                continue
            yield message
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
