from fastmcp import FastMCP


mcp = FastMCP("Biohunter")


@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

