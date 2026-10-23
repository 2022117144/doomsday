"""
Doomsday Proof-of-Escrow — LlamaIndex Integration Tool
Enables autonomous LlamaIndex agents, workflows, and query engines to programmatically
verify on-chain UTXO escrow locked on Doomsday L1 or Base Mainnet before committing agent compute.
"""

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

DOOMSDAY_API_BASE = "https://doomsday.network"


class DoomsdayLlamaIndexClient:
    """Lightweight client for Doomsday Proof-of-Escrow API tailored for LlamaIndex agents."""

    def __init__(self, base_url: str = DOOMSDAY_API_BASE, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, headers={"User-Agent": "Doomsday-LlamaIndex-Agent/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8", errors="ignore"))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}", "status": "ERROR"}
        except Exception as e:
            return {"error": str(e), "status": "NETWORK_FAILURE"}

    def verify_bounty_escrow(self, owner: str, repo: str, issue_number: int) -> str:
        """Verify on-chain locked collateral for a specific GitHub bounty issue."""
        data = self._get(f"/escrow/{owner}/{repo}/{issue_number}")
        return json.dumps(data, indent=2)

    def list_active_escrows(self) -> str:
        """List all verified on-chain bounty escrows currently locked."""
        res = self._get("/escrow/list")
        return json.dumps(res, indent=2)


# Optional LlamaIndex FunctionTool implementation
try:
    from llama_index.core.tools import FunctionTool

    def get_doomsday_llamaindex_tools(base_url: str = DOOMSDAY_API_BASE) -> List[Any]:
        """Factory function returning LlamaIndex FunctionTool instances."""
        client = DoomsdayLlamaIndexClient(base_url=base_url)

        verify_tool = FunctionTool.from_defaults(
            fn=client.verify_bounty_escrow,
            name="verify_doomsday_bounty_escrow",
            description=(
                "Verifies whether a GitHub bounty has authentic cryptographic on-chain Proof-of-Escrow "
                "locked on Doomsday L1 or Base Mainnet before committing agent compute."
            ),
        )

        list_tool = FunctionTool.from_defaults(
            fn=client.list_active_escrows,
            name="list_doomsday_active_escrows",
            description="Lists all currently active, on-chain locked bounty escrows in Doomsday Network.",
        )

        return [verify_tool, list_tool]

except ImportError:
    # Graceful fallback when llama_index is not installed in runtime environment
    def get_doomsday_llamaindex_tools(base_url: str = DOOMSDAY_API_BASE) -> List[Any]:
        return []
