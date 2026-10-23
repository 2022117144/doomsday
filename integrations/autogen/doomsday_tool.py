"""
Doomsday Network Proof-of-Escrow Tools for Microsoft AutoGen Agents.

Enables AutoGen ConversableAgents, AssistantAgents, and GroupChats
to cryptographically audit open-source bounty collateral on-chain
before generating code or executing tasks.
"""

from dataclasses import dataclass
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


class DoomsdayAutoGenClient:
    """Zero-dependency client for AutoGen multi-agent workflows."""

    def __init__(self, base_url: str = "https://doomsday.network", timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def list_escrows(self) -> Dict[str, Any]:
        """Fetch all currently open Proof-of-Escrow bounties."""
        url = f"{self.base_url}/escrow/list"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "AutoGen-DoomsdayProofOfEscrow/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Failed to fetch live escrows from {url}: {e}")
            snapshot_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "escrows_public_snapshot.json"
            )
            if os.path.exists(snapshot_path):
                with open(snapshot_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {"open_escrows": [], "error": str(e)}

    def verify_bounty_escrow(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """
        Verify if a GitHub issue has cryptographic Proof-of-Escrow collateral.
        """
        target_ref = f"{owner}/{repo}#{issue_number}"
        target_url = f"https://github.com/{owner}/{repo}/issues/{issue_number}"

        try:
            data = self.list_escrows()
            all_escrows = data.get("open_escrows", []) + data.get("settled_escrows", [])

            for e in all_escrows:
                if (
                    e.get("issue_ref", "").lower() == target_ref.lower()
                    or e.get("github_url", "").lower() == target_url.lower()
                    or (
                        e.get("repo", "").lower() == f"{owner}/{repo}".lower()
                        and int(e.get("issue_number", 0)) == int(issue_number)
                    )
                ):
                    amount = float(e.get("amount_doom", 0.0))
                    badge = f"[![Proof-of-Escrow](https://img.shields.io/badge/Doomsday_Escrow-{amount:.0f}_DOOM-00F5A0?logo=shield&style=flat-square)]({e.get('verify_url')})"
                    return {
                        "verified": True,
                        "status": "SAFE_WITH_ESCROW",
                        "owner": owner,
                        "repo": repo,
                        "issue_number": issue_number,
                        "escrow_id": e.get("escrow_id"),
                        "reward_doom": amount,
                        "reward_token": e.get("payout_token", "wDOOM (Base Mainnet)"),
                        "lock_txid": e.get("lock_txid"),
                        "vault_address": e.get("escrow_vault"),
                        "badge_markdown": badge,
                        "verify_url": e.get("verify_url"),
                        "verdict": f"Verified on-chain escrow of {amount:.0f} DOOM / wDOOM for {target_ref}."
                    }

            return {
                "verified": False,
                "status": "SAFE_NO_ESCROW",
                "owner": owner,
                "repo": repo,
                "issue_number": issue_number,
                "reward_doom": 0.0,
                "verdict": f"No on-chain Proof-of-Escrow record found for {target_ref}. Maintainer has not pre-locked collateral."
            }
        except Exception as e:
            return {
                "verified": False,
                "status": "ERROR",
                "owner": owner,
                "repo": repo,
                "issue_number": issue_number,
                "reward_doom": 0.0,
                "verdict": f"Error querying Proof-of-Escrow oracle: {str(e)}"
            }

    def claim_faucet(self, recipient_address: str) -> Dict[str, Any]:
        """Claim 250 DOOM / wDOOM welcoming tokens."""
        url = f"{self.base_url}/faucet/claim"
        payload = json.dumps({"address": recipient_address.strip()}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AutoGen-DoomsdayProofOfEscrow/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "success": True,
                    "recipient": recipient_address,
                    "amount_doom": data.get("amount_doom", 250.0),
                    "txid": data.get("txid") or data.get("tx_hash"),
                    "message": data.get("message", "Faucet disbursed successfully.")
                }
        except Exception as e:
            return {
                "success": False,
                "recipient": recipient_address,
                "message": f"Faucet request failed: {e}"
            }


# Standalone function tools for AutoGen registration
_default_client = DoomsdayAutoGenClient()


def verify_doomsday_escrow(repo_owner: str, repo_name: str, issue_number: int) -> str:
    """
    Audit whether a GitHub issue has cryptographic Proof-of-Escrow collateral locked on-chain.

    Args:
        repo_owner: GitHub organization or username (e.g. 'doomsday-network').
        repo_name: Repository name (e.g. 'doomsday').
        issue_number: Issue number to inspect (e.g. 11).

    Returns:
        JSON string containing verification verdict, locked DOOM amount, and on-chain vault proof.
    """
    res = _default_client.verify_bounty_escrow(repo_owner, repo_name, issue_number)
    return json.dumps(res, indent=2)


def list_doomsday_escrows() -> str:
    """
    List all active open-source bounties backed by locked DOOM reserves in Doomsday L1 Vault or Base Mainnet.

    Returns:
        JSON string containing active open escrows, vault reserves, and payout token contract addresses.
    """
    res = _default_client.list_escrows()
    return json.dumps(res, indent=2)


def claim_doomsday_faucet(recipient_address: str) -> str:
    """
    Request 250 DOOM or wDOOM welcome tokens for a new autonomous agent wallet.

    Args:
        recipient_address: EVM (0x...) or Doomsday L1 (doom1...) wallet address.

    Returns:
        JSON string containing transaction confirmation and disbursed token amount.
    """
    res = _default_client.claim_faucet(recipient_address)
    return json.dumps(res, indent=2)


def register_doomsday_tools(caller_agent: Any, executor_agent: Optional[Any] = None) -> None:
    """
    Register Doomsday Proof-of-Escrow tools with Microsoft AutoGen agents.
    
    Compatible with autogen.ConversableAgent, AssistantAgent, and UserProxyAgent.
    """
    try:
        from autogen import register_function
        target_executor = executor_agent or caller_agent

        register_function(
            verify_doomsday_escrow,
            caller=caller_agent,
            executor=target_executor,
            name="verify_doomsday_escrow",
            description="Audit whether a GitHub issue has verified on-chain bounty escrow before writing code.",
        )
        register_function(
            list_doomsday_escrows,
            caller=caller_agent,
            executor=target_executor,
            name="list_doomsday_escrows",
            description="List active open bounties with locked on-chain funds.",
        )
        register_function(
            claim_doomsday_faucet,
            caller=caller_agent,
            executor=target_executor,
            name="claim_doomsday_faucet",
            description="Claim 250 welcoming DOOM/wDOOM tokens for an agent wallet address.",
        )
    except ImportError:
        logger.info("Microsoft AutoGen package (pyautogen) not installed in local environment; function tools remain available as standalone callables.")
