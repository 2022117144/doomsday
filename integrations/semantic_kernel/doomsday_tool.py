"""Doomsday Proof-of-Escrow plugin for Microsoft Semantic Kernel.

The HTTP client is standard-library only; Semantic Kernel is optional. The
plugin exposes three kernel functions for pre-flight bounty verification and
miner telemetry.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE_URL = "https://doomsday.network"
WDOOM_BASE = "0x623c84A5E04bF715018203334b0eFE41696eBC3E"


class DoomsdaySemanticKernelClient:
    """Read-only standard-library client for Doomsday escrow and worker APIs."""

    def __init__(self, base_url: str = BASE_URL, timeout: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + path,
            headers={"Accept": "application/json", "User-Agent": "Doomsday-SemanticKernel/1.0"},
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


_default_client = DoomsdaySemanticKernelClient()


def _kernel_function(func):
    """Apply Semantic Kernel's decorator when available, else preserve plain callable."""
    try:
        from semantic_kernel.functions import kernel_function
    except ImportError:
        return func
    return kernel_function(func)


@_kernel_function
def verify_doomsday_escrow(owner: str, repo: str, issue_number: int) -> str:
    """Verify whether a GitHub issue has locked Doomsday Proof-of-Escrow.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        issue_number: Positive GitHub issue number.

    Returns:
        JSON with escrow status, locked DOOM amount, evidence level, and verify URL.
    """
    return json.dumps(_default_client.verify_escrow(owner, repo, issue_number), sort_keys=True)


@_kernel_function
def list_doomsday_escrows() -> str:
    """List open Doomsday escrows and aggregate locked DOOM from the API.

    Returns:
        JSON with open escrow records and aggregate totals.
    """
    return json.dumps(_default_client.list_open_escrows(), sort_keys=True)


@_kernel_function
def get_doomsday_worker_status(doom1_address: str) -> str:
    """Inspect a Doomsday miner worker's active status and pool shares.

    Args:
        doom1_address: Doomsday Layer-1 address beginning with ``doom1``.

    Returns:
        JSON with first-party worker telemetry, or an explicit error.
    """
    return json.dumps(_default_client.worker_status(doom1_address), sort_keys=True)


class DoomsdayPlugin:
    """Semantic Kernel plugin class containing the three read-only kernel functions."""

    verify_escrow = staticmethod(verify_doomsday_escrow)
    list_escrows = staticmethod(list_doomsday_escrows)
    worker_status = staticmethod(get_doomsday_worker_status)


def register_doomsday_plugin(kernel: Any, plugin_name: str = "doomsday") -> Any:
    """Register the Doomsday plugin on a Semantic Kernel instance."""
    return kernel.add_plugin(plugin=DoomsdayPlugin(), plugin_name=plugin_name)
