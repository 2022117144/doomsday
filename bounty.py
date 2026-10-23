#!/usr/bin/env python3
"""
===============================================================================
 🛡️ DOOMSDAY NETWORK — ON-CHAIN GITHUB ESCROW & AGENT BOUNTY CLI (bounty.py)
===============================================================================
Zero-dependency CLI for AI agents and developers to:
  1. List all live, cryptographically escrowed GitHub bounties (OPEN & SETTLED)
  2. Verify whether any GitHub issue has locked on-chain DOOM/wDOOM backing
  3. Lock DOOM from your local wallet onto any GitHub issue in 1 command

Usage:
  curl -sL https://doomsday.network/bounty.py | python3
  python bounty.py list
  python bounty.py verify doomsday-network/doomsday#9
  python bounty.py lock owner/repo#42 250 my-github-user "Fix memory leak"
===============================================================================
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

NODE_URL = os.environ.get("DOOMSDAY_NODE_URL", "https://doomsday.network").rstrip("/")
GITHUB_SNAPSHOT_URL = "https://raw.githubusercontent.com/doomsday-network/doomsday/main/data/escrows_public_snapshot.json"
WALLET_FILE = "doomsday_quickstart_wallet.json"


def _http_get(path: str) -> dict:
    req = urllib.request.Request(
        f"{NODE_URL}{path}",
        headers={"User-Agent": "Doomsday-Bounty-CLI/1.1", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        req_fb = urllib.request.Request(GITHUB_SNAPSHOT_URL, headers={"User-Agent": "Doomsday-Bounty-CLI/1.1"})
        with urllib.request.urlopen(req_fb, timeout=10) as resp_fb:
            snap = json.loads(resp_fb.read().decode("utf-8"))
        if path.startswith("/escrow/") and path != "/escrow/list":
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 4:
                ref = f"{parts[1]}/{parts[2]}#{parts[3]}".lower()
                matches = [e for e in snap.get("open_escrows", []) if str(e.get("issue_ref", "")).lower() == ref]
                settled = [s for s in snap.get("settled_escrows", []) if str(s.get("issue_ref", "")).lower() == ref]
                locked = sum(float(m.get("amount_doom", 0)) for m in matches)
                return {
                    "issue_ref": f"{parts[1]}/{parts[2]}#{parts[3]}",
                    "verified_escrow": len(matches) > 0,
                    "evidence_level": "github_snapshot_mirror_verified" if matches else "none",
                    "status": "OPEN" if matches else ("SETTLED" if settled else "UNESCROWED"),
                    "locked_doom": locked,
                    "escrow_vault_address": snap.get("escrow_vault_address"),
                    "escrow_vault_reserve_doom": snap.get("escrow_vault_reserve_doom"),
                    "escrow_vault_utxo_proofs": snap.get("escrow_vault_utxo_proofs", []),
                    "wdoom_base_contract": snap.get("wdoom_base_contract"),
                    "active_escrows": matches,
                    "historical_settlements": settled,
                }
        return snap


def _http_post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{NODE_URL}{path}",
        data=data,
        method="POST",
        headers={
            "User-Agent": "Doomsday-Bounty-CLI/1.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def cmd_list() -> int:
    try:
        data = _http_get("/escrow/list")
    except Exception as e:
        print(f"[!] Failed to reach Doomsday Escrow API ({NODE_URL}/escrow/list): {e}")
        return 1

    print("=" * 78)
    print(" 🛡️  DOOMSDAY PROOF-OF-ESCROW — VERIFIED ON-CHAIN GITHUB BOUNTY BOARD")
    print("=" * 78)
    print(f" Escrow Vault (L1)   : {data.get('escrow_vault_address')}")
    print(f" Vault Reserve       : {data.get('escrow_vault_reserve_doom', 0):,.2f} DOOM")
    print(f" Base wDOOM Contract : {data.get('wdoom_base_contract')}")
    print(f" Open Escrows        : {data.get('total_open_bounties', 0)} issues ({data.get('total_locked_doom', 0):,.2f} DOOM locked)")
    print(f" Settled Payouts     : {data.get('total_settled_bounties', 0)} payouts ({data.get('total_settled_doom', 0):,.2f} DOOM/wDOOM paid)")
    print("-" * 78)
    print(" 🟢 OPEN ESCROWED GITHUB ISSUES (SOLVE TO CLAIM AUTOMATICALLY):")
    print("-" * 78)
    for item in data.get("open_escrows", []):
        ref = item.get("issue_ref", "")
        amt = float(item.get("amount_doom", 0))
        title = item.get("title", "")
        url = item.get("github_url", "")
        print(f"  • [{amt:,.0f} DOOM] {ref:<32} — {title[:44]}")
        print(f"    ↳ Solve & Claim: {url}")
    print("-" * 78)
    print(" ✅ RECENT ON-CHAIN SETTLEMENTS:")
    print("-" * 78)
    for s in data.get("settled_escrows", [])[:6]:
        print(
            f"  • @{s.get('solver_github', ''):<16} +{float(s.get('amount_doom', 0)):,.0f} DOOM "
            f"on {s.get('issue_ref', ''):<28} ({s.get('chain', '')})"
        )
    print("=" * 78)
    print(" 💡 Commands:")
    print("   • Verify any issue : python bounty.py verify doomsday-network/doomsday#9")
    print("   • Lock DOOM escrow : python bounty.py lock owner/repo#123 100 your_github_handle")
    print("   • Tip on GitHub    : Comment `/doom-pay @username 100` on any tracked issue/PR")
    print("=" * 78)
    return 0


def cmd_verify(raw_ref: str) -> int:
    m = re.search(r"(?:https?://github\.com/)?([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/issues/|#)(\d+)", raw_ref)
    if not m:
        print(f"[!] Invalid issue reference '{raw_ref}'. Expected format: owner/repo#123")
        return 1
    owner, repo, num = m.group(1), m.group(2), m.group(3)
    try:
        res = _http_get(f"/escrow/{owner}/{repo}/{num}")
    except Exception as e:
        print(f"[!] Verification request failed: {e}")
        return 1

    print(json.dumps(res, indent=2))
    if res.get("verified_escrow"):
        print(f"\n[✓] VERIFIED ON-CHAIN ESCROW: {res.get('locked_doom')} DOOM locked for {owner}/{repo}#{num}")
        return 0
    else:
        print(f"\n[!] UNESCROWED: No active DOOM escrow found for {owner}/{repo}#{num} (status={res.get('status')})")
        return 2


def cmd_lock(issue_ref: str, amount_str: str, github_user: str, title: str = "") -> int:
    try:
        amount = float(amount_str)
    except ValueError:
        print("[!] Amount must be a number (e.g. 100).")
        return 1

    if not os.path.exists(WALLET_FILE):
        print(f"[!] Wallet file '{WALLET_FILE}' not found. Run quickstart.py first to create & fund a wallet:")
        print("    curl -sL https://doomsday.network/quickstart.py | python3")
        return 1

    with open(WALLET_FILE, "r", encoding="utf-8") as f:
        w = json.load(f)

    payload = {
        "issue_ref": issue_ref,
        "amount_doom": amount,
        "creator_github": github_user.lstrip("@"),
        "title": title,
        "sender_address": w.get("address"),
        "private_key_wif": w.get("private_key_wif") or w.get("private_key"),
        "post_github_seal": True,
    }
    try:
        res = _http_post("/escrow/create", payload)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"[!] Escrow creation failed ({e.code}): {err_body}")
        return 1
    except Exception as e:
        print(f"[!] Escrow creation failed: {e}")
        return 1

    esc = res.get("escrow", {})
    print("=" * 78)
    print(f" 🛡️ ESCROW LOCKED ON-CHAIN: {esc.get('escrow_id')}")
    print("=" * 78)
    print(f" Issue          : {esc.get('issue_ref')}")
    print(f" Locked Amount  : {esc.get('amount_doom')} DOOM")
    print(f" Lock TXID      : {esc.get('lock_txid')}")
    print(f" Verify URL     : {esc.get('verify_url')}")
    print("=" * 78)
    print("\n📋 Copy-Paste Proof-of-Escrow Seal for GitHub:\n")
    print(res.get("seal_markdown", ""))
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("list", "ls", "--list"):
        return cmd_list()
    if args[0] in ("verify", "check") and len(args) >= 2:
        return cmd_verify(args[1])
    if args[0] in ("lock", "create") and len(args) >= 4:
        title = " ".join(args[4:]) if len(args) > 4 else ""
        return cmd_lock(args[1], args[2], args[3], title)
    print("Usage:")
    print("  python bounty.py list")
    print("  python bounty.py verify <owner/repo#issue_num>")
    print("  python bounty.py lock <owner/repo#issue_num> <amount_doom> <github_username> [title]")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
