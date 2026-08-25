#!/usr/bin/env python3
"""A tool server for an agent that only talks.

buzz-acp will not finish a turn without an MCP server attached — with none, the
model produces its reply and nothing publishes it. But `buzz-dev-mcp` hands over
`shell`, `read_file` and `str_replace`, and a model holding a shell uses it: a
conversational question turned into six model calls and two minutes while the
agent went looking for an answer it had been told.

So this serves the two lifecycle hooks buzz-acp expects and nothing else. The
front desk keeps its voice, loses the tool loop, and no unrestricted shell sits
behind a chat window. Roles that actually edit a worktree keep buzz-dev-mcp.

Speaks MCP over stdio: one JSON-RPC message per line.
"""
import json
import sys

PROTOCOL = "2025-11-25"

TOOLS = [
    {
        "name": "_Stop",
        "description": ("Returns open todo items if any exist. This agent keeps no "
                        "todo state, so it always reports none and the turn ends."),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "_PostCompact",
        "description": ("Internal hook. Agent invokes after handoff; returns todo "
                        "state for re-injection. This agent carries none."),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


def reply(msg_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\n")
    sys.stdout.flush()


def error(msg_id, code, message):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id,
                                 "error": {"code": code, "message": message}}) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method, msg_id = msg.get("method"), msg.get("id")

        # Notifications carry no id and expect no answer.
        if msg_id is None:
            continue

        if method == "initialize":
            reply(msg_id, {
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "dume-desk-mcp", "version": "1.0.0"},
            })
        elif method == "tools/list":
            reply(msg_id, {"tools": TOOLS})
        elif method == "tools/call":
            name = (msg.get("params") or {}).get("name")
            if name in ("_Stop", "_PostCompact"):
                reply(msg_id, {"content": [{"type": "text", "text": "No open todos."}],
                               "isError": False})
            else:
                # Refusing by name rather than silently succeeding: an agent told a
                # tool worked when it did not will build on the answer.
                error(msg_id, -32601, f"no such tool: {name}")
        elif method in ("resources/list", "prompts/list"):
            reply(msg_id, {"resources": []} if method == "resources/list" else {"prompts": []})
        elif method == "ping":
            reply(msg_id, {})
        else:
            error(msg_id, -32601, f"method not found: {method}")


if __name__ == "__main__":
    main()
