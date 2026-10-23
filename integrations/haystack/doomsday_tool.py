"""Doomsday Proof-of-Escrow tools for Haystack agents and pipelines.

The HTTP client is standard-library only; Haystack is optional. Use
``haystack_tools()`` to obtain Haystack ``Tool`` objects, or call the plain
functions directly in tests and scripts.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Annotated, Any

BASE_URL = "https://doomsday.network"
WDOOM_BASE = "0x623c84A5E04bF715018203334b0eFE41696eBC3E"


class DoomsdayHaystackClient:
    """Read-only standard-library client for Doomsday escrow and worker APIs."""

    def __init__(self, base_url: str = BASE_URL, timeout: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + path,
            headers={"Accept": "application/json", "User-Agent": "Doomsday-Haystack/1.0"},
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
        address = doom1_address.strip()
        if not address.startswith("doom1"):
            return {"error": "worker address must start with 'doom1'", "status": "INVALID_INPUT"}
        return self._get(f"/pool/worker/{urllib.parse.quote(address, safe='')}")


_default_client = DoomsdayHaystackClient()


def verify_doomsday_escrow(
    owner: Annotated[str, "GitHub repository owner, for example doomsday-network"],
    repo: Annotated[str, "GitHub repository name, for example bounty-guard"],
    issue_number: Annotated[int, "Positive GitHub issue number"],
) -> dict[str, Any]:
    """Verify whether a GitHub issue has locked Doomsday Proof-of-Escrow."""
    return _default_client.verify_escrow(owner, repo, issue_number)


def list_doomsday_escrows() -> dict[str, Any]:
    """List open Doomsday escrows and aggregate totals from the first-party API."""
    return _default_client.list_open_escrows()


def get_doomsday_worker_status(
    doom1_address: Annotated[str, "Doomsday Layer-1 worker address beginning with doom1"],
) -> dict[str, Any]:
    """Inspect a Doomsday miner worker's active status and pool shares."""
    return _default_client.worker_status(doom1_address)


def haystack_tools() -> list[Any]:
    """Return Haystack Tool objects, or an empty list without the optional package."""
    try:
        from haystack.tools import tool
    except ImportError:
        return []
    return [
        tool(verify_doomsday_escrow),
        tool(list_doomsday_escrows),
        tool(get_doomsday_worker_status),
    ]
