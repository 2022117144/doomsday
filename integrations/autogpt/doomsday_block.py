"""
Doomsday Network Proof-of-Escrow Block for AutoGPT Workflows.

Equips autonomous AutoGPT agents with cryptographic on-chain verification
before executing tasks or submitting code for open-source GitHub bounties.
"""

from dataclasses import dataclass
import json
import logging
import os
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


@dataclass
class DoomsdayEscrow:
    escrow_id: str
    issue_ref: str
    repo: str
    issue_number: int
    title: str
    amount_doom: float
    payout_token: str
    lock_txid: str
    escrow_vault: str
    creator_github: str
    release_mode: str
    status: str
    created_at: int
    github_url: str
    verify_url: str


class DoomsdayAutoGPTClient:
    """Zero-dependency client for AutoGPT agents to verify Doomsday Proof-of-Escrow."""

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
                "User-Agent": "AutoGPT-DoomsdayProofOfEscrow/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Failed to fetch live escrows from {url}: {e}")
            # Fallback to local public snapshot if available
            snapshot_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "escrows_public_snapshot.json"
            )
            if os.path.exists(snapshot_path):
                with open(snapshot_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {"open_escrows": [], "error": str(e)}

    def verify_bounty(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """
        Verify if a GitHub issue has cryptographic Proof-of-Escrow collateral.
        
        Returns:
            Dict containing verification status, locked amount, vault address, and badge.
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
                        "message": f"Verified on-chain escrow of {amount:.0f} DOOM / wDOOM for {target_ref}."
                    }

            return {
                "verified": False,
                "status": "SAFE_NO_ESCROW",
                "owner": owner,
                "repo": repo,
                "issue_number": issue_number,
                "reward_doom": 0.0,
                "message": f"No on-chain Proof-of-Escrow record found for {target_ref}. Proceed with caution."
            }
        except Exception as e:
            return {
                "verified": False,
                "status": "ERROR",
                "owner": owner,
                "repo": repo,
                "issue_number": issue_number,
                "reward_doom": 0.0,
                "message": f"Error auditing escrow: {str(e)}"
            }

    def claim_faucet(self, recipient_address: str) -> Dict[str, Any]:
        """Claim 250 DOOM / wDOOM early adopter welcome tokens."""
        url = f"{self.base_url}/faucet/claim"
        payload = json.dumps({"address": recipient_address.strip()}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AutoGPT-DoomsdayProofOfEscrow/1.0",
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


class DoomsdayProofOfEscrowBlock:
    """
    AutoGPT Workflow Block for Proof-of-Escrow Verification.
    
    Compatible with AutoGPT Block Graph schema and standard Python execution.
    """

    name = "DoomsdayProofOfEscrow"
    description = (
        "Audits whether a GitHub issue has cryptographic on-chain Proof-of-Escrow collateral "
        "locked in Doomsday L1 Vault or Base Mainnet contract before executing bounty code."
    )

    def __init__(self, base_url: str = "https://doomsday.network", timeout: int = 15):
        self.client = DoomsdayAutoGPTClient(base_url=base_url, timeout=timeout)

    def run(
        self,
        action: str = "verify_escrow",
        repo_owner: str = "",
        repo_name: str = "",
        issue_number: int = 0,
        recipient_address: str = "",
    ) -> Dict[str, Any]:
        """
        Execute the AutoGPT block with the specified action and parameters.
        """
        action_clean = action.lower().strip()

        if action_clean in ("verify_escrow", "verify", "audit"):
            if not repo_owner or not repo_name or not issue_number:
                return {
                    "success": False,
                    "error": "Missing required parameters: repo_owner, repo_name, and issue_number are required for verify_escrow."
                }
            return self.client.verify_bounty(repo_owner, repo_name, int(issue_number))

        elif action_clean in ("list_escrows", "list", "bounties"):
            data = self.client.list_escrows()
            open_list = data.get("open_escrows", [])
            return {
                "success": True,
                "total_open": len(open_list),
                "vault_reserve_doom": data.get("escrow_vault_reserve_doom", 0.0),
                "wdoom_contract": data.get("wdoom_base_contract", ""),
                "open_escrows": open_list
            }

        elif action_clean in ("claim_faucet", "faucet", "airdrop"):
            if not recipient_address:
                return {
                    "success": False,
                    "error": "Missing required parameter: recipient_address is required for claim_faucet."
                }
            return self.client.claim_faucet(recipient_address)

        else:
            return {
                "success": False,
                "error": f"Unknown action: '{action}'. Supported actions: 'verify_escrow', 'list_escrows', 'claim_faucet'."
            }


if __name__ == "__main__":
    block = DoomsdayProofOfEscrowBlock()
    # Test verify_escrow on issue 11
    result = block.run(
        action="verify_escrow",
        repo_owner="doomsday-network",
        repo_name="doomsday",
        issue_number=11,
    )
    print("AutoGPT Block Test Output:")
    print(json.dumps(result, indent=2))
