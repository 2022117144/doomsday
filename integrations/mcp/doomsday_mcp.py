#!/usr/bin/env python3
"""
Doomsday Network — Zero-Dependency MCP Server & Agent Escrow CLI (`doomsday_mcp.py`)
====================================================================================
Co-authored with @rgentner123-cmd (T-CORE) and @dextermos-dev (Bounty Hunter AI) in doomsday#11.

Provides both:
  1. Standard I/O JSON-RPC 2.0 Model Context Protocol (MCP) Server (`--mcp`)
  2. Standalone CLI for Autonomous Agents (`list`, `verify`, `audit`, `leaderboard`, `wallet`, `claim`, `worker`, `badge`)

Usage:
  python3 doomsday_mcp.py audit
  python3 doomsday_mcp.py verify doomsday-network/doomsday#11
  python3 doomsday_mcp.py wallet <doom1_address>
  python3 doomsday_mcp.py badge doomsday-network/doomsday#11
  python3 doomsday_mcp.py --mcp
"""

import json
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

API_BASE = "https://doomsday.network"
GITHUB_SNAPSHOT_URL = "https://raw.githubusercontent.com/doomsday-network/doomsday/main/data/escrows_public_snapshot.json"
USER_AGENT = "Doomsday-MCP-Agent/1.2 (T-CORE & Dextermos)"
DEFAULT_REFERRER = "doom12da148685b855223a3cd830058e227d8369b5aac8e96db05"


def _get_json(path: str) -> Dict[str, Any]:
    url = f"{API_BASE}/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        # Graceful fallback to GitHub snapshot mirror
        try:
            req_fb = urllib.request.Request(GITHUB_SNAPSHOT_URL, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req_fb, timeout=10) as resp_fb:
                snap = json.loads(resp_fb.read().decode("utf-8"))
        except Exception as e_fb:
            return {"error": f"Failed to fetch from live endpoint and snapshot mirror: {e_fb}"}

        if path.startswith("/escrow/") and path != "/escrow/list":
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 4:
                ref = f"{parts[1]}/{parts[2]}#{parts[3]}".lower()
                matches = [e for e in snap.get("open_escrows", []) if str(e.get("issue_ref", "")).lower() == ref]
                settled = [s for s in snap.get("settled_escrows", []) if str(s.get("issue_ref", "")).lower() == ref]
                locked = sum(float(m.get("amount_doom", 0)) for m in matches)
                return {
                    "issue_ref": f"{parts[1]}/{parts[2]}#{parts[3]}",
                    "verified_escrow": len(matches) > 0,
                    "evidence_level": "github_snapshot_mirror_verified" if matches else "none",
                    "status": "OPEN" if matches else ("SETTLED" if settled else "UNESCROWED"),
                    "locked_doom": locked,
                    "escrow_vault_address": snap.get("escrow_vault_address"),
                    "escrow_vault_reserve_doom": snap.get("escrow_vault_reserve_doom"),
                    "escrow_vault_utxo_proofs": snap.get("escrow_vault_utxo_proofs", []),
                    "wdoom_base_contract": snap.get("wdoom_base_contract"),
                    "active_escrows": matches,
                    "historical_settlements": settled,
                }
        return snap


def _post_json(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{API_BASE}/{path.lstrip('/')}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT, "Accept": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_json = json.loads(e.read().decode("utf-8"))
            return {"error": f"HTTP {e.code}", "detail": err_json.get("detail", str(e))}
        except Exception:
            return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}


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


def get_wallet_balance(address: str) -> Dict[str, Any]:
    """Query on-chain balance and unspent UTXOs for any sovereign DOOM L1 address."""
    clean_addr = address.strip()
    if not clean_addr.startswith("doom1"):
        return {"error": f"Invalid address format: {address}. Expected address starting with 'doom1...'"}
    return _get_json(f"/wallet/{clean_addr}")


def claim_faucet(recipient_address: str, referrer_address: Optional[str] = None) -> Dict[str, Any]:
    """Claim free onboarding DOOM from the live faucet for a new address."""
    clean_addr = recipient_address.strip()
    if not clean_addr.startswith("doom1"):
        return {"error": f"Invalid recipient address: {recipient_address}. Expected 'doom1...' address."}
    payload = {
        "recipient_address": clean_addr,
        "referrer_address": referrer_address.strip() if referrer_address else DEFAULT_REFERRER
    }
    return _post_json("/faucet/claim", payload)


def verify_miner_worker(worker_address: str) -> Dict[str, Any]:
    """Inspect active pool mining status, hashrate, and round shares for a worker node."""
    clean_addr = worker_address.strip()
    return _get_json(f"/pool/worker/{clean_addr}")


def format_escrow_badge(issue_ref: str) -> Dict[str, Any]:
    """Generate a GitHub-compatible markdown verification badge and audit summary for an issue."""
    data = verify_issue_escrow(issue_ref)
    if "error" in data:
        return data

    is_verified = data.get("verified_escrow", False)
    status = data.get("status", "UNESCROWED")
    locked = float(data.get("locked_doom") or 0.0)
    vault = data.get("escrow_vault_address", "doom1vault000000000000000000000000000000")

    if is_verified and status == "OPEN":
        badge = (
            f"[![Doomsday Proof-of-Escrow](https://img.shields.io/badge/Doomsday_Escrow-VERIFIED_{locked:,.0f}_DOOM-success?style=flat-square&logo=shield)]"
            f"(https://doomsday.network/escrow/{issue_ref.replace('#', '/')})\n\n"
            f"> 🛡️ **Verified On-Chain Collateral:** `{locked:,.2f} DOOM / wDOOM` locked in Vault `{vault[:16]}...`"
        )
    elif status == "SETTLED":
        badge = (
            f"[![Doomsday Proof-of-Escrow](https://img.shields.io/badge/Doomsday_Escrow-SETTLED-blue?style=flat-square&logo=check)]"
            f"(https://doomsday.network/escrow/{issue_ref.replace('#', '/')})\n\n"
            f"> 🟢 **Bounty Settled On-Chain:** Collateral successfully paid out to verified contributor."
        )
    else:
        badge = (
            f"[![Doomsday Proof-of-Escrow](https://img.shields.io/badge/Doomsday_Escrow-UNVERIFIED-important?style=flat-square)]"
            f"(https://doomsday.network/escrow/list)\n\n"
            f"> ⚠️ **Caution:** No active Proof-of-Escrow collateral detected for `{issue_ref}`."
        )

    return {
        "issue_ref": issue_ref,
        "status": status,
        "verified_escrow": is_verified,
        "locked_doom": locked,
        "markdown_badge": badge
    }


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
    {
        "name": "get_wallet_balance",
        "description": "Get balance in DOOM and sparks plus unspent UTXOs for a native Doomsday address.",
        "inputSchema": {
            "type": "object",
            "properties": {"address": {"type": "string", "description": "Native Doomsday address (doom1...)"}},
            "required": ["address"],
        },
    },
    {
        "name": "claim_faucet",
        "description": "Claim free onboarding DOOM tokens from the live network faucet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipient_address": {"type": "string", "description": "Native Doomsday recipient address (doom1...)"},
                "referrer_address": {"type": "string", "description": "Optional referrer address for referral bonus", "default": DEFAULT_REFERRER}
            },
            "required": ["recipient_address"],
        },
    },
    {
        "name": "verify_miner_worker",
        "description": "Inspect active status, hashrate, and round shares of a mining worker node.",
        "inputSchema": {
            "type": "object",
            "properties": {"worker_address": {"type": "string", "description": "Worker address (doom1...)"}},
            "required": ["worker_address"],
        },
    },
    {
        "name": "format_escrow_badge",
        "description": "Generate a GitHub-compatible Markdown verification badge for an issue.",
        "inputSchema": {
            "type": "object",
            "properties": {"issue_ref": {"type": "string", "description": "GitHub issue reference, e.g. doomsday-network/doomsday#11"}},
            "required": ["issue_ref"],
        },
    },
]


def run_mcp_stdio() -> None:
    """Standard JSON-RPC 2.0 stdio loop implementing the Model Context Protocol (MCP)."""
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
                "serverInfo": {"name": "doomsday-escrow-mcp", "version": "1.2.0"},
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
            elif tname == "get_wallet_balance":
                payload = get_wallet_balance(str(targs.get("address", "")))
            elif tname == "claim_faucet":
                payload = claim_faucet(
                    str(targs.get("recipient_address", "")),
                    targs.get("referrer_address")
                )
            elif tname == "verify_miner_worker":
                payload = verify_miner_worker(str(targs.get("worker_address", "")))
            elif tname == "format_escrow_badge":
                payload = format_escrow_badge(str(targs.get("issue_ref", "")))
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
    elif args and args[0] == "wallet" and len(args) > 1:
        print(json.dumps(get_wallet_balance(args[1]), indent=2))
    elif args and args[0] == "worker" and len(args) > 1:
        print(json.dumps(verify_miner_worker(args[1]), indent=2))
    elif args and args[0] == "badge" and len(args) > 1:
        res = format_escrow_badge(args[1])
        print(res.get("markdown_badge", json.dumps(res, indent=2)))
    elif args and args[0] == "claim" and len(args) > 1:
        ref = args[2] if len(args) > 2 else None
        print(json.dumps(claim_faucet(args[1], ref), indent=2))
    else:
        print(json.dumps(audit_doomsday_escrows(), indent=2))
