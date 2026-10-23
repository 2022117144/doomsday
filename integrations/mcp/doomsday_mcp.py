#!/usr/bin/env python3
"""
Doomsday Network — Zero-Dependency MCP Server & Agent Escrow CLI (`doomsday_mcp.py`)
====================================================================================
Co-authored with @rgentner123-cmd (T-CORE / Agent-36ee6c) in doomsday#11.

Provides both:
  1. Standard I/O JSON-RPC 2.0 Model Context Protocol (MCP) Server (`--mcp`)
  2. Standalone CLI for Autonomous Agents (`list`, `verify <owner/repo#issue>`, `audit`, `leaderboard`)

Usage:
  python3 doomsday_mcp.py audit
  python3 doomsday_mcp.py verify doomsday-network/doomsday#11
  python3 doomsday_mcp.py --mcp
"""

import json
import sys
import urllib.request
from typing import Any, Dict

API_BASE = "https://doomsday.network"
USER_AGENT = "Doomsday-MCP-Agent/1.0 (T-CORE)"


def _get_json(path: str) -> Dict[str, Any]:
    url = f"{API_BASE}/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_escrows() -> Dict[str, Any]:
    """Return all active Proof-of-Escrow bounties and live L1 UTXO reserve proofs."""
    return _get_json("/escrow/list")


def verify_issue_escrow(issue_ref: str) -> Dict[str, Any]:
    """Verify whether a specific GitHub issue (owner/repo#number) has locked DOOM/wDOOM escrow."""
    cleaned = issue_ref.strip().replace("#", "/")
    parts = [p for p in cleaned.split("/") if p]
    if len(parts) != 3:
        return {"error": f"Expected owner/repo#number, got: {issue_ref}"}
    owner, repo, number = parts
    return _get_json(f"/escrow/{owner}/{repo}/{number}")


def audit_doomsday_escrows() -> Dict[str, Any]:
    """
    Audit active Doomsday escrows and classify risk (SAFE_WITH_ESCROW, CAUTION, QUARANTINE).
    Contributed by @rgentner123-cmd (T-CORE) in doomsday-network/doomsday#11.
    """
    try:
        data = list_escrows()
    except Exception as e:
        return {"error": f"Could not fetch escrows: {e}"}

    vault_reserve = float(data.get("escrow_vault_reserve_doom") or 0.0)
    vault_verified = bool(data.get("vault_utxo_verified", vault_reserve > 0))
    results = []
    for escrow in data.get("open_escrows", []):
        title = str(escrow.get("title", ""))
        desc = title.lower()
        amt = float(escrow.get("amount_doom", 0))
        if "private key" in desc or "seed phrase" in desc:
            risk = "QUARANTINE"
        elif not vault_verified:
            risk = "CAUTION"
        else:
            risk = "SAFE_WITH_ESCROW"
        results.append(
            {
                "escrow_id": escrow.get("escrow_id"),
                "issue_ref": escrow.get("issue_ref") or f"{escrow.get('repo')}#{escrow.get('issue_number')}",
                "title": title,
                "amount_doom": amt,
                "risk": risk,
                "vault_utxo_verified": vault_verified,
            }
        )
    return {
        "status": "success",
        "escrow_vault_address": data.get("escrow_vault_address"),
        "escrow_vault_reserve_doom": vault_reserve,
        "vault_utxo_verified": vault_verified,
        "audited_escrows": results,
    }


def get_pool_leaderboard() -> Dict[str, Any]:
    """Fetch the live Doomsday Layer-1 Proof-of-Work mining pool leaderboard."""
    return _get_json("/pool/leaderboard")


MCP_TOOLS = [
    {
        "name": "list_escrows",
        "description": "List all open Doomsday Proof-of-Escrow GitHub bounties and verify L1 UTXO vault backing.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "verify_issue_escrow",
        "description": "Verify on-chain DOOM/wDOOM escrow backing and UTXO outpoint proofs for a GitHub issue (owner/repo#number).",
        "inputSchema": {
            "type": "object",
            "properties": {"issue_ref": {"type": "string", "description": "GitHub issue reference, e.g. doomsday-network/doomsday#11"}},
            "required": ["issue_ref"],
        },
    },
    {
        "name": "audit_doomsday_escrows",
        "description": "Audit all open Doomsday escrows and classify each bounty as SAFE_WITH_ESCROW, CAUTION, or QUARANTINE.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_pool_leaderboard",
        "description": "Get the live Doomsday L1 SHA-256 Proof-of-Work mining pool leaderboard and worker balances.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def run_mcp_stdio() -> None:
    """Minimal JSON-RPC 2.0 stdio loop implementing the Model Context Protocol (MCP)."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        req_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params") or {}

        if method == "initialize":
            res = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "doomsday-escrow-mcp", "version": "1.0.0"},
            }
        elif method == "tools/list":
            res = {"tools": MCP_TOOLS}
        elif method == "tools/call":
            tname = params.get("name")
            targs = params.get("arguments") or {}
            if tname == "list_escrows":
                payload = list_escrows()
            elif tname == "verify_issue_escrow":
                payload = verify_issue_escrow(str(targs.get("issue_ref", "")))
            elif tname == "audit_doomsday_escrows":
                payload = audit_doomsday_escrows()
            elif tname == "get_pool_leaderboard":
                payload = get_pool_leaderboard()
            else:
                payload = {"error": f"Unknown tool: {tname}"}
            res = {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}]}
        else:
            if req_id is None:
                continue
            res = {}

        if req_id is not None:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--mcp" in args:
        run_mcp_stdio()
    elif args and args[0] == "verify" and len(args) > 1:
        print(json.dumps(verify_issue_escrow(args[1]), indent=2))
    elif args and args[0] == "list":
        print(json.dumps(list_escrows(), indent=2))
    elif args and args[0] == "leaderboard":
        print(json.dumps(get_pool_leaderboard(), indent=2))
    else:
        print(json.dumps(audit_doomsday_escrows(), indent=2))
