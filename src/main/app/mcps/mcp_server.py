from fastmcp import FastMCP

mcp = FastMCP("Biohunter")


@mcp.tool()
def get_weather(name: str) -> dict:
    """
    通过名字获取天气
    """
    return {"result": f"{name} 的天气是晴天!"}
