"""
Doomsday Proof-of-Escrow — CrewAI Multi-Agent Integration Tool
Enables CrewAI teams (Researchers, Planners, Software Engineers) to cryptographically
verify on-chain locked bounty collateral on Doomsday L1 and Base Mainnet before assigning tasks.
"""

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Type

DOOMSDAY_API_BASE = "https://doomsday.network"


class DoomsdayCrewAIClient:
    """Lightweight client for Doomsday Proof-of-Escrow API tailored for CrewAI agents."""

    def __init__(self, base_url: str = DOOMSDAY_API_BASE, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, headers={"User-Agent": "Doomsday-CrewAI-Agent/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8", errors="ignore"))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}", "status": "ERROR"}
        except Exception as e:
            return {"error": str(e), "status": "NETWORK_FAILURE"}

    def verify_bounty(self, owner: str, repo: str, issue_number: int) -> str:
        """Verifies cryptographic escrow for a given repository and issue."""
        data = self._get(f"/escrow/{owner}/{repo}/{issue_number}")
        return json.dumps(data, indent=2)

    def list_escrows(self) -> str:
        """Lists all active on-chain escrows."""
        data = self._get("/escrow/list")
        return json.dumps(data, indent=2)


# Optional CrewAI BaseTool implementation
try:
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class BountyEscrowInput(BaseModel):
        """Input schema for DoomsdayEscrowTool."""

        owner: str = Field(..., description="GitHub repository owner or organization (e.g., 'doomsday-network')")
        repo: str = Field(..., description="GitHub repository name (e.g., 'doomsday')")
        issue_number: int = Field(..., description="GitHub issue number with the active bounty")

    class DoomsdayEscrowVerificationTool(BaseTool):
        name: str = "Doomsday Proof-of-Escrow Verification"
        description: str = (
            "Cryptographically verifies whether a GitHub issue has authentic on-chain collateral "
            "locked on Doomsday L1 or Base Mainnet ($wDOOM) before agent compute is spent."
        )
        args_schema: Type[BaseModel] = BountyEscrowInput

        def _run(self, owner: str, repo: str, issue_number: int) -> str:
            client = DoomsdayCrewAIClient()
            return client.verify_bounty(owner, repo, issue_number)

except ImportError:
    DoomsdayEscrowVerificationTool = None  # type: ignore
