# SPDX-License-Identifier: MIT
"""FastMCP client"""

import asyncio
from collections.abc import Mapping
from typing import Any

from autogen_core import CancellationToken, Image
from autogen_core.tools import (
    ImageResultContent,
    ParametersSchema,
    TextResultContent,
    ToolResult,
    ToolSchema,
    Workbench,
)
from fastmcp import Client
from mcp.types import CallToolResult, EmbeddedResource, ImageContent, TextContent


class FastMCPWorkbench(Workbench):
    """
    A workbench that wraps a FastMCP client to list and call tools.

    Args:
        client: The FastMCP client to use to list and call tools.
    """

    def __init__(self, client: Client):
        self.client = client

    async def list_tools(self) -> list[ToolSchema]:
        list_tools_result = await self.client.list_tools_mcp()
        return [
            ToolSchema(
                name=tool.name,
                description=tool.description or "",
                parameters=ParametersSchema(
                    type="object",
                    properties=tool.inputSchema.get("properties", {}),
                    required=tool.inputSchema.get("required", []),
                    additionalProperties=tool.inputSchema.get(
                        "additionalProperties", False
                    ),
                ),
            )
            for tool in list_tools_result.tools
        ]

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> ToolResult:
        if not cancellation_token:
            cancellation_token = CancellationToken()
        if not arguments:
            arguments = {}
        try:
            result_future = asyncio.create_task(
                self.client.call_tool_mcp(name, arguments)
            )
            cancellation_token.link_future(result_future)
            result = await result_future
            assert isinstance(result, CallToolResult), (
                f"call_tool must return a CallToolResult, instead of : {str(type(result))}"
            )
            result_parts: list[TextResultContent | ImageResultContent] = []
            is_error = result.isError
            for content in result.content:
                if isinstance(content, TextContent):
                    result_parts.append(TextResultContent(content=content.text))
                elif isinstance(content, ImageContent):
                    result_parts.append(
                        ImageResultContent(content=Image.from_base64(content.data))
                    )
                elif isinstance(content, EmbeddedResource):
                    # TODO: how to handle embedded resources?
                    # For now we just use text representation.
                    result_parts.append(
                        TextResultContent(content=content.model_dump_json())
                    )
                else:
                    raise ValueError(
                        f"Unknown content type from server: {type(content)}"
                    )
        except Exception as e:
            error_message = str(e)
            is_error = True
            result_parts = [TextResultContent(content=error_message)]
        return ToolResult(name=name, result=result_parts, is_error=is_error)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def reset(self) -> None:
        pass

    async def save_state(self) -> Mapping[str, Any]:
        return {}

    async def load_state(self, state: Mapping[str, Any]) -> None:
        pass

    async def __aenter__(self):
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
