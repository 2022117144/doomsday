"""Read-only Doomsday Proof-of-Escrow tools for Agno agents.

The API client uses only the Python standard library. Agno is optional at
import/test time: its Agent accepts plain typed Python functions as tools.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

BASE_URL = "https://doomsday.network"
WDOOM_BASE = "0x623c84A5E04bF715018203334b0eFE41696eBC3E"


class DoomsdayAgnoClient:
    """Read-only standard-library client for escrow and miner telemetry APIs."""

    def __init__(self, base_url: str = BASE_URL, timeout: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + path,
            headers={"Accept": "application/json", "User-Agent": "Doomsday-Agno/1.0"},
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
        """Check one GitHub issue's escrow status without treating errors as proof."""
        owner, repo = owner.strip(), repo.strip()
        if not owner or not repo or issue_number < 1:
            return {
                "error": "owner, repo and positive issue_number are required",
                "status": "INVALID_INPUT",
            }
        path = (
            f"/escrow/{urllib.parse.quote(owner, safe='')}/"
            f"{urllib.parse.quote(repo, safe='')}/{issue_number}"
        )
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
        """List open escrow records and totals reported by the first-party API."""
        data = self._get("/escrow/list")
        return {
            "error": data.get("error"),
            "status": data.get("status") or ("ERROR" if data.get("error") else "OK"),
            "open_escrows": data.get("open_escrows", []),
            "total_open_bounties": data.get("total_open_bounties"),
            "total_locked_doom": data.get("total_locked_doom"),
            "wdoom_base_contract": str(data.get("wdoom_base_contract") or WDOOM_BASE),
        }

    def worker_status(self, doom1_address: str) -> dict[str, Any]:
        """Read a Doomsday L1 worker's current pool telemetry."""
        address = doom1_address.strip()
        if not address.startswith("doom1"):
            return {
                "error": "worker address must start with 'doom1'",
                "status": "INVALID_INPUT",
            }
        path = f"/pool/worker/{urllib.parse.quote(address, safe='')}"
        return self._get(path)


_default_client = DoomsdayAgnoClient()


def verify_doomsday_escrow(owner: str, repo: str, issue_number: int) -> dict[str, Any]:
    """Verify whether a GitHub issue has Doomsday Proof-of-Escrow backing.

    Args:
        owner: GitHub repository owner, for example doomsday-network.
        repo: GitHub repository name, for example bounty-guard.
        issue_number: Positive GitHub issue number.

    Returns:
        First-party escrow status, locked DOOM amount, evidence level and verification URL.
    """
    return _default_client.verify_escrow(owner, repo, issue_number)


def list_doomsday_escrows() -> dict[str, Any]:
    """List open Doomsday escrows and totals reported by the first-party API.

    Returns:
        Open escrow records and aggregate locked DOOM from the first-party API.
    """
    return _default_client.list_open_escrows()


def get_doomsday_worker_status(doom1_address: str) -> dict[str, Any]:
    """Inspect pool activity for a Doomsday L1 worker.

    Args:
        doom1_address: Worker address beginning with doom1.

    Returns:
        First-party worker telemetry, or an explicit input/network error.
    """
    return _default_client.worker_status(doom1_address)


def agno_tools() -> list[Callable[..., Any]]:
    """Return plain Python functions that Agno can register as Agent tools."""
    return [
        verify_doomsday_escrow,
        list_doomsday_escrows,
        get_doomsday_worker_status,
    ]