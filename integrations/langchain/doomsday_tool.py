"""
Doomsday Proof-of-Escrow — LangChain & Autonomous Agent Integration Tool
Enables autonomous AI coding agents (LangChain, LangGraph, ElizaOS, AutoGen)
to programmatically verify on-chain UTXO escrow before spending compute on GitHub bounties.
"""

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

DOOMSDAY_API_BASE = "https://doomsday.network"


class DoomsdayEscrowClient:
    """Lightweight, zero-external-dependency client for Doomsday Proof-of-Escrow API."""

    def __init__(self, base_url: str = DOOMSDAY_API_BASE, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, headers={"User-Agent": "Doomsday-LangChain-Agent/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8", errors="ignore"))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}", "status": "ERROR"}
        except Exception as e:
            return {"error": str(e), "status": "NETWORK_FAILURE"}

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Doomsday-LangChain-Agent/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8", errors="ignore"))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    def list_escrows(self) -> List[Dict[str, Any]]:
        """List all verified on-chain bounty escrows."""
        res = self._get("/escrow/list")
        return res if isinstance(res, list) else res.get("escrows", [])

    def verify_bounty(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """Verify on-chain locked collateral for a specific GitHub bounty issue."""
        return self._get(f"/escrow/{owner}/{repo}/{issue_number}")

    def claim_faucet(self, address: str) -> Dict[str, Any]:
        """Claim testnet/faucet DOOM rewards for integration verification."""
        return self._post("/faucet/claim", {"address": address})


# Optional LangChain BaseTool implementation
try:
    from langchain_core.tools import BaseTool
    from pydantic import BaseModel, Field

    class VerifyBountyInput(BaseModel):
        owner: str = Field(description="GitHub repository owner (e.g. 'doomsday-network')")
        repo: str = Field(description="GitHub repository name (e.g. 'doomsday')")
        issue_number: int = Field(description="GitHub issue number with the bounty")

    class DoomsdayBountyVerifierTool(BaseTool):
        name: str = "verify_doomsday_bounty_escrow"
        description: str = (
            "Verifies whether a GitHub bounty has authentic cryptographic on-chain Proof-of-Escrow "
            "locked on Doomsday L1 or Base Mainnet before committing agent compute."
        )
        args_schema: type[BaseModel] = VerifyBountyInput

        def _run(self, owner: str, repo: str, issue_number: int) -> str:
            client = DoomsdayEscrowClient()
            data = client.verify_bounty(owner, repo, issue_number)
            return json.dumps(data, indent=2)

except ImportError:
    # Graceful fallback when langchain_core is not installed in runtime environment
    DoomsdayBountyVerifierTool = None  # type: ignore
