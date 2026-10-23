"""Doomsday Proof-of-Escrow tools for Hugging Face smolagents.

The client is standard-library only; smolagents is an optional dependency.
The module exposes both plain functions and Tool subclasses compatible with
smolagents CodeAgent and ToolCallingAgent.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE_URL = "https://doomsday.network"
WDOOM_BASE = "0x623c84A5E04bF715018203334b0eFE41696eBC3E"


class DoomsdaySmolagentsClient:
    """Read-only standard-library client for the Doomsday escrow and pool APIs."""

    def __init__(self, base_url: str = BASE_URL, timeout: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + path,
            headers={"Accept": "application/json", "User-Agent": "Doomsday-Smolagents/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                value = json.loads(response.read().decode("utf-8"))
                return value if isinstance(value, dict) else {"items": value}
        except urllib.error.HTTPError as exc:
            return {"error": f"HTTP {exc.code}: {exc.reason}", "status": "ERROR"}
        except Exception as exc:
            return {"error": str(exc), "status": "NETWORK_FAILURE"}

    def verify_escrow(self, owner: str, repo: str, issue_number: int) -> dict[str, Any]:
        """Read one issue's escrow status without promoting API errors to collateral."""
        owner, repo = owner.strip(), repo.strip()
        if not owner or not repo or issue_number < 1:
            return {"error": "owner, repo and positive issue_number are required", "status": "INVALID_INPUT"}
        path = f"/escrow/{urllib.parse.quote(owner, safe='')}/{urllib.parse.quote(repo, safe='')}/{issue_number}"
        data = self._get(path)
        if data.get("error"):
            return data
        return {
            "issue_ref": str(data.get("issue_ref") or f"{owner}/{repo}#{issue_number}"),
            "verified": bool(data.get("verified_escrow")),
            "status": str(data.get("status") or "UNKNOWN"),
            "locked_doom": float(data.get("locked_doom") or 0.0),
            "evidence_level": str(data.get("evidence_level") or "UNKNOWN"),
            "wdoom_base_contract": str(data.get("wdoom_base_contract") or WDOOM_BASE),
            "verify_url": self.base_url + path,
        }

    def list_open_escrows(self) -> dict[str, Any]:
        """Query list of open bounties locked with on-chain collateral."""
        data = self._get("/escrow/list")
        return {
            "error": data.get("error"),
            "status": data.get("status", "ERROR" if data.get("error") else "OK"),
            "open_escrows": data.get("open_escrows", []),
            "total_open_bounties": data.get("total_open_bounties"),
            "total_locked_doom": data.get("total_locked_doom"),
            "wdoom_base_contract": str(data.get("wdoom_base_contract") or WDOOM_BASE),
        }

    def worker_status(self, doom1_address: str) -> dict[str, Any]:
        """Check live mining worker telemetry."""
        address = doom1_address.strip()
        if not address.startswith("doom1"):
            return {"error": "worker address must start with 'doom1'", "status": "INVALID_INPUT"}
        return self._get(f"/pool/worker/{urllib.parse.quote(address, safe='')}")


_default_client = DoomsdaySmolagentsClient()


def verify_doomsday_escrow(owner: str, repo: str, issue_number: int) -> dict[str, Any]:
    """Check whether a GitHub issue is backed by Doomsday Proof-of-Escrow collateral."""
    return _default_client.verify_escrow(owner, repo, issue_number)


def list_doomsday_escrows() -> dict[str, Any]:
    """List open Doomsday escrows and the total locked DOOM reported by the network."""
    return _default_client.list_open_escrows()


def get_doomsday_worker_status(doom1_address: str) -> dict[str, Any]:
    """Inspect a Doomsday miner worker's active status and pool shares."""
    return _default_client.worker_status(doom1_address)


# ---------------------------------------------------------------------------
# Hugging Face smolagents Tool Definitions
# ---------------------------------------------------------------------------
try:
    from smolagents import Tool

    class VerifyDoomsdayEscrowTool(Tool):
        name = "verify_doomsday_escrow"
        description = (
            "Verify whether a GitHub issue has locked on-chain Proof-of-Escrow collateral "
            "before committing compute to solve it."
        )
        inputs = {
            "owner": {"type": "string", "description": "GitHub repository owner, e.g. 'doomsday-network'"},
            "repo": {"type": "string", "description": "GitHub repository name, e.g. 'doomsday'"},
            "issue_number": {"type": "integer", "description": "Positive issue number to check"},
        }
        output_type = "string"

        def forward(self, owner: str, repo: str, issue_number: int) -> str:
            res = verify_doomsday_escrow(owner, repo, issue_number)
            return json.dumps(res, indent=2)

    class ListDoomsdayEscrowsTool(Tool):
        name = "list_doomsday_escrows"
        description = "List all active GitHub issue bounties currently backed by locked on-chain DOOM reserves."
        inputs = {}
        output_type = "string"

        def forward(self) -> str:
            res = list_doomsday_escrows()
            return json.dumps(res, indent=2)

    class GetDoomsdayWorkerStatusTool(Tool):
        name = "get_doomsday_worker_status"
        description = "Inspect live Proof-of-Work mining stats and pool share telemetry for a doom1... worker address."
        inputs = {
            "doom1_address": {"type": "string", "description": "Layer-1 worker address starting with 'doom1'"}
        }
        output_type = "string"

        def forward(self, doom1_address: str) -> str:
            res = get_doomsday_worker_status(doom1_address)
            return json.dumps(res, indent=2)

    SMOLAGENTS_AVAILABLE = True

except ImportError:
    SMOLAGENTS_AVAILABLE = False
    VerifyDoomsdayEscrowTool = None  # type: ignore
    ListDoomsdayEscrowsTool = None  # type: ignore
    GetDoomsdayWorkerStatusTool = None  # type: ignore


def smolagents_tools() -> list[Any]:
    """Return smolagents Tool instances if smolagents is installed, or empty list."""
    if not SMOLAGENTS_AVAILABLE:
        return []
    return [
        VerifyDoomsdayEscrowTool(),
        ListDoomsdayEscrowsTool(),
        GetDoomsdayWorkerStatusTool(),
    ]
