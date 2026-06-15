"""
GitHub remote MCP -> SecureMCPProxy with bind_to_user.

Two tests, one file. Calls go: client identity -> server identity -> upstream,
so MACAW renders a two-node graph (client ──> server) for both tests.

  Test 1 (active by default):  one bound.call_tool("get_me") then exit.
  Test 2 (uncomment block):    stdio MCP gateway for Gemini/Claude CLI.

Run:
    export GITHUB_PERSONAL_ACCESS_TOKEN="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"
    /home/itsadijmbt/MACAW-MCP-STORE/venv/bin/python3.11 \\
        TEST_SERVERS/SECURE-PROXY-SERVER-SCRIPTS/github/proxy_github.py
"""

import os
import sys
import logging
from macaw_adapters.mcp import SecureMCPProxy, Client


logging.basicConfig(level=logging.INFO, stream=sys.stderr)

token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
if not token:
    raise ValueError("GITHUB_PERSONAL_ACCESS_TOKEN is not set")

proxy = SecureMCPProxy(
    app_name="github-remote-proxy",
    upstream_url="https://api.githubcopilot.com/mcp/",
    upstream_auth={"type": "bearer", "token": token},
)


client = Client("github-remote-proxy")
bound = proxy.bind_to_user(client.macaw_client)


tools = proxy.list_tools()
print(f"tools: {len(tools)}", file=sys.stderr)
for t in tools:
    print(f"  - {t['name']}: {t.get('description','')[:80]}", file=sys.stderr)

result = bound.call_tool("get_me", {})
print(f"\nget_me -> {str(result)[:300]}", file=sys.stderr)


print("\n" + "=" * 60, file=sys.stderr)
print("GITHUB PROXY RED-TEAM", file=sys.stderr)
print("=" * 60, file=sys.stderr)


def test(label, name, args):
    print(f"\n[{label}] {name} {str(args)[:80]}", file=sys.stderr)
    try:
        r = bound.call_tool(name, args)
        print(f"  -> {str(r)[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"  -> Failed: {str(e)[:200]}", file=sys.stderr)



O = {"owner": "macaw-redteam", "repo": "probe"}  

# # --- DENY: crown jewels in denied_resources (reason names tool:github-remote-proxy/<tool>) ---
test("DENY actions_run_trigger (CI -> RCE in runners + secrets)", "actions_run_trigger",
     {**O, "method": "run_workflow", "workflow_id": "ci.yml", "ref": "main"})
test("DENY create_or_update_file (code injection)", "create_or_update_file",
     {**O, "path": "app.py", "content": "x", "message": "m", "branch": "main"})
test("DENY merge_pull_request (ship unreviewed code)", "merge_pull_request",
     {**O, "pullNumber": 1})
# test("DENY fork_repository (private-code exfil)", "fork_repository", {**O})
# test("DENY create_gist (exfil channel)", "create_gist",
#      {"filename": "x.txt", "content": "stolen", "public": True})
# test("DENY list_secret_scanning_alerts (secret EXFIL read)", "list_secret_scanning_alerts", {**O})
# test("DENY projects_write (org board manipulation)", "projects_write",
#      {"method": "org", "owner_type": "org", "owner": "macaw-redteam"})
# test("DENY remove_sub_issue (destructive unlink)", "remove_sub_issue",
#      {**O, "issue_number": 1, "sub_issue_id": 2})
# test("DENY dismiss_notification (anti-forensics)", "dismiss_notification",
#      {"threadID": "1", "state": "read"})

# # --- THE METHOD LEVER: allowed_values pins each consolidated write tool to safe
# #     sub-ops, so destructive methods are blocked BY OMISSION (param constraint). ---
# test("DENY label_write method=delete (not in allowed_values [create,update])", "label_write",
#      {**O, "method": "delete", "name": "bug"})
# test("DENY discussion_comment_write method=delete (allowlist excludes delete)",
#      "discussion_comment_write", {**O, "method": "delete", "commentNodeID": "x"})
# test("DENY sub_issue_write method=remove (allowlist [add,reprioritize])", "sub_issue_write",
#      {**O, "method": "remove", "issue_number": 1, "sub_issue_id": 2})
# test("DENY issue_read method=create (read tool pinned to read methods)", "issue_read",
#      {**O, "method": "create", "issue_number": 1})

# # --- denied_parameters (proxy-enforced): block secret-file paths on get_file_contents ---
# test("DENY get_file_contents path=.env (secret-file block)", "get_file_contents",
#      {**O, "path": ".env"})
# test("DENY get_file_contents path=config/credentials.json (secret-file block)",
#      "get_file_contents", {**O, "path": "config/credentials.json"})

# # --- ALLOW: authoring writes + reads (forward to GitHub; need a valid PAT) ---
# test("ALLOW create_issue (authoring -> expect forward+result)", "create_issue",
#      {**O, "title": "macaw probe", "body": "b"})
# test("ALLOW label_write method=create (safe method -> forward)", "label_write",
#      {**O, "method": "create", "name": "macaw-probe", "color": "ededed"})
# test("ALLOW issue_read method=get (allowed read method)", "issue_read",
#      {**O, "method": "get", "issue_number": 1})
# test("ALLOW get_file_contents path=README.md (clean path)", "get_file_contents",
#      {**O, "path": "README.md"})
# test("ALLOW get_me / search_repositories (reads)", "search_repositories",
#      {"query": "stars:>10000 language:go"})

