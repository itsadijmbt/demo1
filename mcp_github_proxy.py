

import os
import sys
import json
import asyncio
import logging

from macaw_adapters.mcp import SecureMCPProxy, Client
from macaw_client import MACAWClient, RemoteIdentityProvider

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types


logging.basicConfig(level=logging.INFO, stream=sys.stderr)


# --- face B: the proxy + bound client (live in THIS process) -------------
token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
if not token:
    raise ValueError("GITHUB_PERSONAL_ACCESS_TOKEN is not set")

# Startup ~= (#tools) x ~1.3s, because the proxy registers EACH upstream tool as
# its own ToolAgent via a remote register_agent call to api.macawsecurity.ai.
# The full /mcp/ exposes 44 tools (~60s) which blows Claude's 60s per-request
# `initialize` timeout -> -32001. Use a smaller GitHub TOOLSET so registration
# finishes inside the window (override with GITHUB_MCP_URL):
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

_user = os.environ.get("MACAW_USER")
_pw = os.environ.get("PASSWORD")
if _user and _pw:
    jwt_token, _ = RemoteIdentityProvider().login(_user, _pw)      
    user_client = MACAWClient(
        app_name = f"github-macaw-{_user}",
        agent_type="user",
        user_name=_user,
        iam_token=jwt_token,
    )
    print(f"[gateway_1_a] bound to REAL user '{_user}' via RemoteIdentityProvider JWT",
          file=sys.stderr)
else:
    user_client = Client("github-macaw").macaw_client
    print("[gateway_1_a] no MACAW_USER/MACAW_PASSWORD -> static gateway identity",
          file=sys.stderr)

bound = proxy.bind_to_user(user_client)

_tools = proxy.list_tools()
print(f"[gateway_1_a] proxy live -- {len(_tools)} tools discovered", file=sys.stderr)


# MACAW's endpoint being called from a MCP-compliant-server.
srv = Server("github-macaw")


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
    # Relay into the mesh as the bound user identity. A MAPL deny raises here;
    # surface it as text so Claude shows the refusal instead of crashing.
    try:
        result = bound.call_tool(name, arguments or {})
        text = json.dumps(result, default=str) if isinstance(result, (dict, list)) \
            else str(result)
    except Exception as e:
        text = f"MACAW deny / upstream error: {e}"
    return [types.TextContent(type="text", text=text)]


async def _serve():
    print("[gateway_1_a] serving stdio MCP -> relaying to github-remote-proxy",
          file=sys.stderr)
    async with stdio_server() as (rd, wr):
        await srv.run(rd, wr, srv.create_initialization_options())


if __name__ == "__main__":
     asyncio.run(_serve())
