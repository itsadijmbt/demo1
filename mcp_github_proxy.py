

import os
import sys
import json
import asyncio
import logging

from macaw_adapters.mcp import SecureMCPProxy, Client

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types


logging.basicConfig(level=logging.INFO, stream=sys.stderr)


token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
if not token:
    raise ValueError("GITHUB_PERSONAL_ACCESS_TOKEN is not set")

#   /mcp/                  44 tools  ~60s   
#   /mcp/readonly          27 tools  ~35s
#   /mcp/x/repos           19 tools  ~25s
#   /mcp/x/repos/readonly  13 tools  ~17s   safe default
GITHUB_MCP_URL = os.environ.get(
    "GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/x/repos/readonly")

proxy = SecureMCPProxy(
    app_name="github-remote-proxy",
    upstream_url=GITHUB_MCP_URL,
    upstream_auth={"type": "bearer", "token": token},
)

 
client = Client("secure-claudecode")
bound = proxy.bind_to_user(client.macaw_client)

_tools = proxy.list_tools()
print(f"[gateway_1_a] proxy live -- {len(_tools)} tools discovered", file=sys.stderr)


# MACAW's endpoint being called from a secCC via a MCP-Compliant server.
srv = Server("secureClaudeCode")


@srv.list_tools()
async def _list_tools():
    # proxy tool dicts are {"name","description","schema"} (proxy.py:184-188);
    # MCP wants inputSchema, so map "schema" -> inputSchema.
    return [
        types.Tool(
            name=t["name"],
            description=t.get("description", ""),
            inputSchema=t.get("schema") or {"type": "object"},
        )
        for t in proxy.list_tools()
    ]


@srv.call_tool()
async def _call_tool(name, arguments):

    try:
        result = bound.call_tool(name, arguments or {})
        text = json.dumps(result, default=str) if isinstance(result, (dict, list)) \
            else str(result)
    except Exception as e:
        text = f"MACAW deny / upstream error: {e}"
    return [types.TextContent(type="text", text=text)]


async def _serve():
    async with stdio_server() as (rd, wr):
        await srv.run(rd, wr, srv.create_initialization_options())


if __name__ == "__main__":
     asyncio.run(_serve())
