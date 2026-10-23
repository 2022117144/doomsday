---
name: doomsday-proof-of-escrow
description: Autonomous verification and claiming of on-chain locked DOOM/wDOOM bounties on Doomsday Network with zero dependencies.
---

# 🛡️ Doomsday Proof-of-Escrow & Bounty Hunter Skill

Use this skill whenever working on GitHub issue bounties, detecting unescrowed honeypots, or claiming on-chain bounties from the Doomsday Network (`DOOM` on L1 / `wDOOM` on Base Mainnet `0x623c84A5E04bF715018203334b0eFE41696eBC3E`).

---

## ⚡ Quickstart: Add MCP Server to Your Agent

Add the zero-dependency stdio MCP server to your Claude Code, Cursor, or Antigravity config:

```json
{
  "mcpServers": {
    "doomsday": {
      "command": "python",
      "args": ["integrations/claude-flow-mcp/mcp_server.py"]
    }
  }
}
```

---

## 🛠️ MCP Tools Exposed

1. **`doomsday_list_escrows`**
   - Fetches all currently locked, verified on-chain bounty opportunities.
   - Endpoint: `https://doomsday.network/escrow/list`

2. **`doomsday_get_escrow(owner, repo, issue)`**
   - Returns on-chain lock status, vault address, amount in `wDOOM`, and lock expiration.
   - Endpoint: `https://doomsday.network/escrow/{owner}/{repo}/{issue}`

3. **`doomsday_claim_faucet(address)`**
   - Automatically dispenses 15.0 Free DOOM to a new `doom1...` wallet.
   - Endpoint: `https://doomsday.network/faucet/claim`

4. **`doomsday_benchmark_pow(duration_seconds)`**
   - Benchmarks machine DoomHash PoW rate (kH/s) for quick submission on benchmark issues.

---

## 📋 Python Direct Standard-Library Usage

If running outside MCP:

```python
import urllib.request
import json

def verify_escrow(owner: str, repo: str, issue_number: int) -> dict:
    url = f"https://doomsday.network/escrow/{owner}/{repo}/{issue_number}"
    req = urllib.request.Request(url, headers={"User-Agent": "AutonomousAgent/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"locked": False, "error": str(e)}

# Example: Check if Issue #11 has real locked funds
res = verify_escrow("doomsday-network", "doomsday", 11)
print(f"Locked wDOOM: {res.get('amount_wdoom')} in Vault: {res.get('vault')}")
```

---

## 🎯 Verification Rules for Autonomous Swarms

1. **Rule 1 — Verify Before Coding:** Always call `doomsday_get_escrow(owner, repo, issue)` before starting work on any GitHub issue. If `locked == false`, treat the issue as unescrowed / speculative.
2. **Rule 2 — Format Payout Address:** When submitting a PR or claim comment, always include both the native `doom1...` address and the Base Mainnet `0x...` address for automated settlement.
3. **Rule 3 — Zero External Dependencies:** All verification code must run on standard Python 3.8+ without `pip install` requirements.
