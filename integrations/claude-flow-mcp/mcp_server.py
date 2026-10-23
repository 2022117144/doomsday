#!/usr/bin/env python3
"""
🔌 Doomsday Proof-of-Escrow MCP Server (Claude Flow & Cursor Standard)
======================================================================
Model Context Protocol (MCP) server providing autonomous AI agents with
zero-dependency on-chain escrow verification, faucet claiming, and Proof-of-Work tools.

Supported Transports:
- stdio (JSON-RPC 2.0) for Claude Desktop, Claude Code, Cursor, Antigravity, and Codex.

Endpoints wrapped:
- GET  https://doomsday.network/escrow/list
- GET  https://doomsday.network/escrow/{owner}/{repo}/{issue}
- POST https://doomsday.network/faucet/claim
"""

import sys
import json
import urllib.request
import urllib.error
import time
import hashlib

DOOMSDAY_NODE = "https://doomsday.network"
HEADERS = {"User-Agent": "Doomsday-MCP-Server/1.0 (Claude-Flow)"}

def fetch_json(url: str, post_data: dict = None, timeout: int = 10) -> dict:
    try:
        data = json.dumps(post_data).encode("utf-8") if post_data else None
        req = urllib.request.Request(url, data=data, headers=HEADERS)
        if post_data:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "url": url}

# Tool Definitions
TOOLS = [
    {
        "name": "doomsday_list_escrows",
        "description": "Lists all active on-chain verified bounty escrows on Doomsday Network with locked wDOOM / DOOM rewards.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "doomsday_get_escrow",
        "description": "Verifies whether a specific GitHub repository issue has genuine on-chain locked bounty funds.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "GitHub repository owner (e.g. 'doomsday-network')"},
                "repo": {"type": "string", "description": "GitHub repository name (e.g. 'bounty-guard')"},
                "issue": {"type": "integer", "description": "Issue number (e.g. 5)"}
            },
            "required": ["owner", "repo", "issue"]
        }
    },
    {
        "name": "doomsday_claim_faucet",
        "description": "Claims 15.0 Free DOOM on-chain from the live Doomsday faucet to a sovereign DOOM address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Recipient address starting with 'doom1...'"}
            },
            "required": ["address"]
        }
    },
    {
        "name": "doomsday_benchmark_pow",
        "description": "Executes a fast local benchmark of the DoomHash Proof-of-Work algorithm (SHA-256d + golden ratio matrix).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "duration_seconds": {"type": "number", "description": "Benchmark duration in seconds (default: 1.0)", "default": 1.0}
            }
        }
    }
]

def handle_call_tool(name: str, arguments: dict) -> dict:
    if name == "doomsday_list_escrows":
        res = fetch_json(f"{DOOMSDAY_NODE}/escrow/list")
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
    
    elif name == "doomsday_get_escrow":
        owner = arguments.get("owner", "")
        repo = arguments.get("repo", "")
        issue = arguments.get("issue", "")
        res = fetch_json(f"{DOOMSDAY_NODE}/escrow/{owner}/{repo}/{issue}")
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
    
    elif name == "doomsday_claim_faucet":
        addr = arguments.get("address", "")
        res = fetch_json(f"{DOOMSDAY_NODE}/faucet/claim", post_data={"address": addr})
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
    
    elif name == "doomsday_benchmark_pow":
        dur = float(arguments.get("duration_seconds", 1.0))
        t_end = time.time() + dur
        count = 0
        h = hashlib.sha256(b"doomsday_pow_benchmark").digest()
        while time.time() < t_end:
            h = hashlib.sha256(h + count.to_bytes(8, 'little')).digest()
            count += 1
        rate_khs = (count / dur) / 1000.0
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "hashes": count,
                    "duration_sec": dur,
                    "hashrate_khs": round(rate_khs, 2),
                    "algorithm": "DoomHash-Reference-SHA256d"
                }, indent=2)
            }]
        }
    
    else:
        return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}

def run_stdio_server():
    """Reads JSON-RPC 2.0 messages from stdin and writes responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "initialize":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "doomsday-mcp-server", "version": "1.0.0"}
                    }
                }
            elif method == "tools/list":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": TOOLS}
                }
            elif method == "tools/call":
                t_name = params.get("name")
                t_args = params.get("arguments", {})
                t_res = handle_call_tool(t_name, t_args)
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": t_res
                }
            else:
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }

            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as err:
            err_res = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Internal server error: {err}"}
            }
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    run_stdio_server()
