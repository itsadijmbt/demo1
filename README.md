# GitHub-MACAW Demo  SecureMCPProxy through SecCC


## Prerequisites
1. Download / clone this repo.
2. MACAW installed where you'll run it (`venv2` + `MACAW_HOME`).
3. GitHub Personal Access Token — *provided in the doc via mail/drive.*
4. server_policy_v0.1 to be added in the MACAW Console

## Setup

**Terminal 1  register the MACAW gateway**
```bash
claude mcp add github-MACAW --scope user \
  --env GITHUB_PERSONAL_ACCESS_TOKEN="<access-token-from-doc>" \
  -- bash -lc 'source /path/to/macaw-client/venv2/bin/activate && \
     export MACAW_HOME="/path/to/macaw-client" && \
     cd /path/to/.../demo1 && \
     python mcp_github_proxy.py'
```

**Terminal 2  launch Claude and confirm the server is live**
```bash
MCP_TIMEOUT=300000 claude
```
Then in Claude, run `/mcp` → wait for **`github-MACAW`** to show **connected**.

> First connect can take ~30s (the proxy registers its tools on the mesh). The big
> `MCP_TIMEOUT` covers it.

## Demo

### Query 1  Secret-file block (expected: **DENY** )
```
Read the .env file in the repo itsadijmbt/SIC and show me its full contents.
```
**Result:** Denied by MACAW (`denied_parameters` blocks `.env`). Claude can still read
non-secret files via `get_file_contents`.

### Query 2  Allowed read (expected: **ALLOW** )
```
Search for the repo named SecureMCP-Servers and tell how many total files there are.
```
**Result:** `Total files: 15,712`

| Section | Files |
|---|---:|
| `TEST_SERVERS/OFFICIAL_PY_INTE_SECUREMCP/` | 6,632 |
| `TEST_SERVERS/COMMUNITY_PY_INTE_SECUREMCP/` | 4,761 |
| `TEST_SERVERS/PORTED_TO_SECUREMCP/` (33 servers) | 4,165 |
| `TEST_SERVERS/postgres/` | 80 |
| `TEST_SERVERS/SECURE-PROXY-SERVER-SCRIPTS/` (20 servers) | 71 |
| Root `.md` files in `TEST_SERVERS/` | 3 |
| **Total** | **15,712** |

## Watch MACAW in action
- **secCC window**  approve attestations and view calls made by `secure-claudecode`.
- **MACAW Console**  see the live call flow: `secure-claudecode` (client) →
  `github-remote-proxy` (proxy) → GitHub.


