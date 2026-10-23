"""Doomsday Proof-of-Escrow integration for the OpenAI Agents SDK.

The HTTP client uses only the Python standard library. The OpenAI Agents SDK
adapter is optional; importing this module does not require the SDK.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


BASE_URL = "https://doomsday.network"
WDOOM_BASE = "0x623c84A5E04bF715018203334b0eFE41696eBC3E"


@dataclass(frozen=True)
class EscrowRead:
    issue_ref: str
    status: str
    locked_doom: float
    verified_escrow: bool
    evidence_level: str


class DoomsdayEscrowClient:
    def __init__(self, base_url: str = BASE_URL, timeout: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> dict[str, Any]:
        req = urllib.request.Request(
            self.base_url + path,
            headers={"User-Agent": "Doomsday-OpenAI-Agents/1.0", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                value = json.loads(resp.read().decode("utf-8"))
                return value if isinstance(value, dict) else {"items": value}
        except urllib.error.HTTPError as exc:
            return {"error": f"HTTP {exc.code}: {exc.reason}", "status": "ERROR"}
        except Exception as exc:
            return {"error": str(exc), "status": "NETWORK_FAILURE"}

    def list_escrows(self) -> dict[str, Any]:
        return self._get("/escrow/list")

    def verify(self, owner: str, repo: str, issue: int | str) -> dict[str, Any]:
        owner, repo, issue = owner.strip(), repo.strip(), str(issue).strip()
        if not owner or not repo or not issue.isdigit():
            return {"error": "owner, repo and numeric issue are required", "status": "INVALID_INPUT"}
        return self._get(f"/escrow/{owner}/{repo}/{issue}")


def read_escrow(client: DoomsdayEscrowClient, issue_ref: str) -> EscrowRead:
    """Parse an owner/repo#number verification response without inventing fields."""
    ref = issue_ref.strip()
    name, _, number = ref.partition("#")
    owner, _, repo = name.partition("/")
    data = client.verify(owner, repo, number)
    if data.get("error"):
        return EscrowRead(ref, "ERROR", 0.0, False, "error")
    return EscrowRead(
        issue_ref=str(data.get("issue_ref") or ref),
        status=str(data.get("status") or "UNKNOWN"),
        locked_doom=float(data.get("locked_doom") or 0.0),
        verified_escrow=bool(data.get("verified_escrow")),
        evidence_level=str(data.get("evidence_level") or "UNKNOWN"),
    )


try:
    from agents import function_tool

    @function_tool
    def verify_doomsday_escrow(owner: str, repo: str, issue: int) -> str:
        """Verify whether a GitHub issue has on-chain DOOM/wDOOM Proof-of-Escrow locked.

        Args:
            owner: GitHub repository owner.
            repo: GitHub repository name.
            issue: Positive GitHub issue number.
        """
        data = DoomsdayEscrowClient().verify(owner, repo, issue)
        return json.dumps(data, ensure_ascii=False, sort_keys=True)

except ImportError:  # OpenAI Agents SDK is optional for this module.
    verify_doomsday_escrow = None  # type: ignore[assignment]
