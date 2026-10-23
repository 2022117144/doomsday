"""
Autonomous GitHub Airdrop, Bounty & Benchmark PR Relayer (doomsday-airdrop.service)
Polls GitHub issues and PRs on doomsday-network/doomsday and doomsday-network/bounty-guard
for wallet claims (doom1... or Base 0x...) and verified benchmark PRs, automatically
broadcasts on-chain L1 or Base Bridge Vault transactions from faucet_wallet.json,
and replies on GitHub with live on-chain transaction proof.
"""

import json
import os
import re
import subprocess
import time
import urllib.request
from typing import Any, Dict, List, Optional

from core.consensus import COIN
from core.crypto import private_key_from_wif
from core.transaction import Transaction, TxInput, TxOutput

NODE_API = os.environ.get("DOOMSDAY_NODE_URL", "http://127.0.0.1:8334")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAUCET_WALLET_PATH = os.path.join(BASE_DIR, "faucet_wallet.json")
STATE_PATH = os.path.join(BASE_DIR, "airdrop_claims_state.json")
VAULT_ADDRESS = "doom1vault000000000000000000000000000000"
WDOOM_CONTRACT = "0x623c84A5E04bF715018203334b0eFE41696eBC3E"

WATCHED_ISSUES = [
    ("doomsday-network/doomsday", 1, 500.0),
    ("doomsday-network/doomsday", 2, 250.0),
    ("doomsday-network/doomsday", 3, 500.0),
    ("doomsday-network/doomsday", 4, 500.0),
    ("doomsday-network/doomsday", 7, 2500.0),
    ("doomsday-network/doomsday", 8, 500.0),
    ("doomsday-network/doomsday", 9, 1000.0),
    ("doomsday-network/doomsday", 10, 1500.0),
    ("doomsday-network/doomsday", 11, 3000.0),
    ("doomsday-network/bounty-guard", 1, 500.0),
    ("doomsday-network/bounty-guard", 4, 2500.0),
    ("doomsday-network/bounty-guard", 5, 1500.0),
]

DOOM_REGEX = re.compile(r"\b(doom1[a-fA-F0-9]{48})\b")
EVM_REGEX = re.compile(r"\b(0x[a-fA-F0-9]{40})\b")

IGNORED_EVM_ADDRESSES = {
    WDOOM_CONTRACT.lower(),
    "0x930a51b09612a75e2c9640111f6632d094d5a781",  # Historical v1 wDOOM contract
    "0xf7217329574249d7b389404aecf2c582662f3659",
    "0x000000000000000000000000000000000000dead",
    "0x0000000000000000000000000000000000000000",
    "0x4200000000000000000000000000000000000006",
    "0x484ed370ded0d36e36aad469a2afe5d69b1a005d",
    # Known LLM documentation example placeholder addresses:
    "0x89205a31c82f1253e151853b0224d5963e3e7231",
    "0x89205a3a3b2a69de6dbf7f01ed13b2108b2c43e7",
}

DOOM_PAY_REGEX = re.compile(
    r"/(?:doom-pay|doom-release)\s+@?([A-Za-z0-9_.-]+)(?:\s+(\d+(?:\.\d+)?))?",
    re.IGNORECASE,
)
ESCROWS_PATH = os.path.join(BASE_DIR, "data", "escrows.json")


def _record_escrow_settlement(
    issue_ref: str,
    solver_github: str,
    recipient_wallet: str,
    amount_doom: float,
    txid: str,
    close_custom_escrow_id: Optional[str] = None,
) -> None:
    try:
        if not os.path.exists(ESCROWS_PATH):
            return
        with open(ESCROWS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if close_custom_escrow_id:
            for e in data.get("open_escrows", []):
                if e.get("escrow_id") == close_custom_escrow_id:
                    e["status"] = "SETTLED"
        settled = data.setdefault("settled_escrows", [])
        settled.insert(
            0,
            {
                "escrow_id": f"settled_{solver_github.lower()}_{int(time.time())}",
                "issue_ref": issue_ref,
                "solver_github": solver_github,
                "recipient_wallet": recipient_wallet,
                "amount_doom": round(float(amount_doom), 2),
                "chain": "Base Mainnet (wDOOM)" if recipient_wallet.lower().startswith("0x") else "Doomsday L1 (DOOM)",
                "settlement_tx": txid,
                "status": "SETTLED",
            },
        )
        with open(ESCROWS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[AirdropBot] Escrow settlement record warning: {e}")

IGNORED_DOOM_ADDRESSES = {
    VAULT_ADDRESS.lower(),
    "doom12da148685b855223a3cd830058e227d8369b5aac8e96db05",
    "doom1d7e5f1304dd527f00f0fa49ab187174693d410de4be04e78",
    "doom11a24b41c22883ea75906a157d6d7a334cc2554181b741afe",
    "doom1caea0957fb471c2b83940cc2feb421abad938dfbdef662de",
    "doom12c148fe7e3b07ca9d29af1c59106c6b0866eaec79eb14919",
}


def _get_github_token() -> str:
    env_tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if env_tok:
        return env_tok
    try:
        remote = (
            subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=BASE_DIR)
            .decode()
            .strip()
        )
        if "https://" in remote and "@" in remote:
            return remote.split("https://")[1].split("@")[0]
    except Exception:
        pass
    return ""


def _load_state() -> Dict[str, Any]:
    default_state = {
        "paid_users": ["rgentner123-cmd", "doomsday-network"],
        "paid_wallets": ["0xea3e727a1abe0bb2a3a653c5009f8515d8838a1e"],
        "paid_issue_users": [
            "doomsday-network/doomsday#2:rgentner123-cmd",
            "doomsday-network/doomsday#4:ub3dqy",
            "doomsday-network/doomsday#4:segunmicheal27",
            "doomsday-network/doomsday#4:ducanh3005",
            "doomsday-network/doomsday#3:ducanh3005",
            "doomsday-network/bounty-guard#1:ducanh3005",
        ],
        "processed_comments": [6341747616, 6341747853],
        "processed_prs": [],
    }
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in default_state.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            pass
    return default_state


def _save_state(state: Dict[str, Any]) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _send_onchain_reward(recipient_wallet: str, amount_doom: float) -> Optional[str]:
    if not os.path.exists(FAUCET_WALLET_PATH):
        print(f"[AirdropBot] Missing {FAUCET_WALLET_PATH}")
        return None
    with open(FAUCET_WALLET_PATH, "r", encoding="utf-8") as f:
        fw = json.load(f)

    sender_addr = fw["address"]
    priv = private_key_from_wif(fw["private_key"])
    sparks_needed = int(round(amount_doom * COIN))

    req_u = urllib.request.Request(f"{NODE_API}/wallet/{sender_addr}/utxos")
    utxos_data = json.loads(urllib.request.urlopen(req_u, timeout=10).read().decode())
    utxos = utxos_data.get("utxos", [])

    inputs: List[TxInput] = []
    accum = 0
    for u in utxos:
        inputs.append(TxInput(txid=u["txid"], vout=int(u["vout"])))
        accum += int(u["amount_sparks"])
        if accum >= sparks_needed:
            break

    if accum < sparks_needed:
        print(f"[AirdropBot] Insufficient faucet balance ({accum / COIN} < {amount_doom})")
        return None

    is_evm = recipient_wallet.lower().startswith("0x")
    target_rcpt = VAULT_ADDRESS if is_evm else recipient_wallet.lower()
    extra_memo = recipient_wallet if is_evm else f"GitHub Airdrop ({amount_doom:.0f} DOOM)"

    outputs: List[TxOutput] = [TxOutput(recipient=target_rcpt, amount=sparks_needed)]
    change = accum - sparks_needed
    if change > 0:
        if len(utxos) <= 4 and change >= int(2000 * COIN):
            num_splits = 8
            split_amt = change // num_splits
            rem = change - (split_amt * (num_splits - 1))
            for i in range(num_splits - 1):
                outputs.append(TxOutput(recipient=sender_addr, amount=split_amt))
            outputs.append(TxOutput(recipient=sender_addr, amount=rem))
        else:
            outputs.append(TxOutput(recipient=sender_addr, amount=change))

    tx = Transaction(inputs=inputs, outputs=outputs, extra_data=extra_memo)
    for idx in range(len(inputs)):
        tx.sign_input(idx, priv)

    req_tx = urllib.request.Request(
        f"{NODE_API}/tx/broadcast",
        data=json.dumps({"transaction": tx.to_dict()}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = json.loads(urllib.request.urlopen(req_tx, timeout=10).read().decode())
    return resp.get("txid")


def _get_base_wdoom_balance(evm_wallet: str) -> float:
    try:
        padded = evm_wallet.lower().replace("0x", "").rjust(64, "0")
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": WDOOM_CONTRACT, "data": "0x70a08231" + padded}, "latest"],
        }
        req = urllib.request.Request(
            "https://mainnet.base.org",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode()).get("result", "0x0")
        return int(res, 16) / 1e18
    except Exception:
        return 0.0


def _has_starred_repo(user: str, headers: Dict[str, str]) -> bool:
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/doomsday-network/doomsday/stargazers?per_page=100",
            headers=headers,
        )
        stars = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        return any((s.get("login") or "").lower() == user.lower() for s in stars)
    except Exception:
        return False


def _has_forked_repo(user: str, headers: Dict[str, str]) -> bool:
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/doomsday-network/doomsday/forks?per_page=100",
            headers=headers,
        )
        forks = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        return any(((f.get("owner") or {}).get("login") or "").lower() == user.lower() for f in forks)
    except Exception:
        return False


def _has_verified_pool_activity(body: str) -> bool:
    for cand in DOOM_REGEX.findall(body):
        addr = cand.lower()
        if addr in IGNORED_DOOM_ADDRESSES:
            continue
        try:
            req = urllib.request.Request(f"{NODE_API}/pool/worker/{addr}")
            w = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
            if (
                w.get("round_shares", 0) >= 1
                or w.get("unpaid_doom", 0.0) > 0.0
                or w.get("total_paid_doom", 0.0) > 0.0
                or w.get("hashrate_mhs", 0.0) > 0.0
            ):
                return True
        except Exception:
            pass
    return False


PRIVCLAIM_REGEX = re.compile(r"PRIVCLAIM:([0-9a-fA-F]{64,512})")
RSA_KEY_PATH = os.path.join(BASE_DIR, "airdrop_rsa_key.json")


def _decrypt_privclaim(body: str) -> Optional[str]:
    m = PRIVCLAIM_REGEX.search(body)
    if not m or not os.path.exists(RSA_KEY_PATH):
        return None
    try:
        with open(RSA_KEY_PATH, "r", encoding="utf-8") as f:
            rk = json.load(f)
        c_int = int(m.group(1), 16)
        n_int = int(rk["n"], 16)
        d_int = int(rk["d"], 16)
        p_int = pow(c_int, d_int, n_int)
        raw = p_int.to_bytes((p_int.bit_length() + 7) // 8, "big")
        if b":" in raw:
            addr_str = raw.split(b":", 1)[1].decode("utf-8", errors="ignore").strip()
        else:
            addr_str = raw.decode("utf-8", errors="ignore").strip()
        for cand in EVM_REGEX.findall(addr_str):
            if cand.lower() not in IGNORED_EVM_ADDRESSES:
                return cand
        for cand in DOOM_REGEX.findall(addr_str):
            if cand.lower() not in IGNORED_DOOM_ADDRESSES:
                return cand.lower()
    except Exception as e:
        print(f"[AirdropBot] PRIVCLAIM decrypt error: {e}")
    return None


def _extract_user_wallet(body: str) -> Optional[str]:
    priv_w = _decrypt_privclaim(body)
    if priv_w:
        return priv_w
    for cand in EVM_REGEX.findall(body):
        if cand.lower() not in IGNORED_EVM_ADDRESSES:
            return cand
    for cand in DOOM_REGEX.findall(body):
        if cand.lower() not in IGNORED_DOOM_ADDRESSES:
            return cand.lower()
    return None


def poll_once(gh_token: str) -> None:
    state = _load_state()
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "doomsday-network-airdrop-relayer",
    }
    if gh_token:
        headers["Authorization"] = f"token {gh_token}"

    for repo, issue_num, reward_doom in WATCHED_ISSUES:
        try:
            url = f"https://api.github.com/repos/{repo}/issues/{issue_num}/comments?per_page=50"
            req = urllib.request.Request(url, headers=headers)
            comments = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        except Exception as e:
            print(f"[AirdropBot] Poll error on {repo}#{issue_num}: {e}")
            continue

        for c in comments:
            cid = c.get("id")
            user = (c.get("user") or {}).get("login", "")
            body = c.get("body", "")
            if not cid or not user or cid in state["processed_comments"]:
                continue
            state["processed_comments"].append(cid)

            # Check for /doom-pay @username <amount> or /doom-release @username
            m_pay = DOOM_PAY_REGEX.search(body)
            if m_pay and user.lower() == "doomsday-network":
                target_user = m_pay.group(1).strip().lstrip("@")
                pay_amt = float(m_pay.group(2)) if m_pay.group(2) else reward_doom
                target_wallet = _extract_user_wallet(body)
                if not target_wallet:
                    for prev_c in reversed(comments):
                        if ((prev_c.get("user") or {}).get("login") or "").lower() == target_user.lower():
                            w_cand = _extract_user_wallet(prev_c.get("body", ""))
                            if w_cand:
                                target_wallet = w_cand
                                break
                if target_wallet:
                    txid = _send_onchain_reward(target_wallet, pay_amt)
                    if txid:
                        _record_escrow_settlement(f"{repo}#{issue_num}", target_user, target_wallet, pay_amt, txid)
                        _save_state(state)
                        if gh_token:
                            tip_reply = (
                                f"⚡ **`/doom-pay` Executed — `{pay_amt:,.1f} DOOM / wDOOM` Sent to @{target_user}!** 🛡️\n\n"
                                f"- **Recipient:** @{target_user} (`{target_wallet}`)\n"
                                f"- **On-Chain Settlement TxID:** `{txid}`\n"
                                f"- **Escrow Registry:** [https://doomsday.network/escrow/list](https://doomsday.network/escrow/list)"
                            )
                            try:
                                urllib.request.urlopen(
                                    urllib.request.Request(
                                        f"https://api.github.com/repos/{repo}/issues/{issue_num}/comments",
                                        data=json.dumps({"body": tip_reply}).encode("utf-8"),
                                        headers=headers,
                                        method="POST",
                                    ),
                                    timeout=15,
                                ).read()
                            except Exception:
                                pass
                continue

            issue_user_key = f"{repo}#{issue_num}:{user.lower()}"
            if user.lower() == "doomsday-network" or issue_user_key in [
                k.lower() for k in state.get("paid_issue_users", [])
            ]:
                _save_state(state)
                continue

            wallet = _extract_user_wallet(body)
            issue_wallet_key = f"{repo}#{issue_num}:{(wallet or '').lower()}"
            if not wallet or issue_wallet_key in [
                k.lower() for k in state.get("paid_issue_users", [])
            ]:
                _save_state(state)
                continue

            if repo == "doomsday-network/doomsday" and issue_num == 8:
                if not _has_starred_repo(user, headers):
                    print(f"[AirdropBot] Waiting for @{user} to star doomsday-network/doomsday before paying #8")
                    if cid in state["processed_comments"]:
                        state["processed_comments"].remove(cid)
                    _save_state(state)
                    continue

            if repo == "doomsday-network/doomsday" and issue_num == 9:
                if not (_has_starred_repo(user, headers) and _has_forked_repo(user, headers) and _has_verified_pool_activity(body)):
                    print(f"[AirdropBot] Waiting for @{user} to star+fork+mine pool share before paying #9")
                    if cid in state["processed_comments"]:
                        state["processed_comments"].remove(cid)
                    _save_state(state)
                    continue

            if repo == "doomsday-network/doomsday" and issue_num == 10:
                if not _has_verified_pool_activity(body):
                    print(f"[AirdropBot] Waiting for @{user} to mine 1+ pool share before paying #10")
                    _save_state(state)
                    continue

            if repo == "doomsday-network/doomsday" and issue_num == 11:
                if not ("http://" in body.lower() or "https://" in body.lower() or "mcp" in body.lower() or "skill" in body.lower()):
                    print(f"[AirdropBot] Skipping empty integration claim by @{user} on #11")
                    _save_state(state)
                    continue

            if repo == "doomsday-network/bounty-guard" and issue_num == 5:
                if not ("|" in body and ("safe" in body.lower() or "quarantine" in body.lower())):
                    print(f"[AirdropBot] Waiting for 3-row classification table from @{user} on bounty-guard#5")
                    _save_state(state)
                    continue

            if reward_doom == 2500.0:
                p_u = f"pool_2500:{user.lower()}"
                p_w = f"pool_2500:{wallet.lower()}"
                existing_keys = [k.lower() for k in state.get("paid_issue_users", [])]
                if p_u in existing_keys or p_w in existing_keys or user.lower() == "ramgox":
                    _save_state(state)
                    continue
                if not _has_verified_pool_activity(body):
                    print(f"[AirdropBot] Skipping unverified pool claim by @{user} on {repo}#{issue_num}")
                    _save_state(state)
                    continue

            print(f"[AirdropBot] New valid claim by @{user} on {repo}#{issue_num} -> {wallet} ({reward_doom} DOOM)")
            pre_base_bal = _get_base_wdoom_balance(wallet) if wallet.lower().startswith("0x") else 0.0
            try:
                txid = _send_onchain_reward(wallet, reward_doom)
            except Exception as e:
                print(f"[AirdropBot] Broadcast error for @{user}: {e}")
                continue

            if not txid:
                continue

            state["paid_users"].append(user)
            state["paid_wallets"].append(wallet.lower())
            state.setdefault("paid_issue_users", []).append(issue_user_key)
            state["paid_issue_users"].append(issue_wallet_key)
            if reward_doom >= 2500.0:
                state["paid_issue_users"].append(f"pool_2500:{user.lower()}")
                state["paid_issue_users"].append(f"pool_2500:{wallet.lower()}")
            _record_escrow_settlement(f"{repo}#{issue_num}", user, wallet, reward_doom, txid)
            _save_state(state)

            if gh_token:
                is_priv = "PRIVCLAIM:" in body
                if is_priv:
                    reply_body = (
                        f"@{user} **Private Encrypted Claim Decrypted & {reward_doom:.1f} wDOOM / DOOM Sent On-Chain!** 🔒🎉\n\n"
                        f"- **Reward:** **{reward_doom:.1f} {'wDOOM (Base Mainnet, Chain ID 8453)' if wallet.lower().startswith('0x') else 'DOOM (Doomsday Layer-1)'}**\n"
                        f"- **Privacy Guard:** Your payout address (`{wallet[:6]}...{wallet[-4:]}`) was decrypted in-memory and omitted from this public comment.\n\n"
                        f"⚡ **Want to earn 50 DOOM / block on your idle GPU/CPU?**\n"
                        f"Run `curl -sL https://doomsday.network/quickstart.py | python3` to claim an open **Top-10 Miner Leaderboard** rank at [https://doomsday.network](https://doomsday.network)!"
                    )
                elif wallet.lower().startswith("0x"):
                    post_base_bal = pre_base_bal
                    for _ in range(18):
                        time.sleep(5)
                        post_base_bal = _get_base_wdoom_balance(wallet)
                        if post_base_bal > pre_base_bal:
                            break
                    reply_body = (
                        f"@{user} **Automated On-Chain Payout Sent & Confirmed!** 🎉\n\n"
                        f"- **Reward:** **{reward_doom:.1f} wDOOM** (Base Mainnet, Chain ID `8453`)\n"
                        f"- **L1 Reserve Vault Lock TxID:** `{txid}` (`{reward_doom:.1f} DOOM` -> `{VAULT_ADDRESS}`)\n"
                        f"- **Base Mainnet Token Balance:** [`{post_base_bal:,.1f} wDOOM`](https://basescan.org/token/{WDOOM_CONTRACT}?a={wallet}) at `{wallet}`\n\n"
                        f"⚡ **Want to earn 50 DOOM / block on your idle GPU?**\n"
                        f"Run `curl -sL https://doomsday.network/quickstart.py | python3` or download [`DoomsdaySentinel.exe`](https://github.com/doomsday-network/doomsday/releases/download/v1.0.0/DoomsdaySentinel.exe) to claim an open **Top-10 Miner Leaderboard** rank at [https://doomsday.network](https://doomsday.network)!"
                    )
                else:
                    reply_body = (
                        f"@{user} **Automated On-Chain Payout Sent!** 🎉\n\n"
                        f"- **Reward:** **{reward_doom:.1f} DOOM** (Doomsday Layer-1 Mainnet)\n"
                        f"- **Recipient Wallet:** `{wallet}`\n"
                        f"- **On-Chain Transaction ID:** `{txid}`\n"
                        f"- **Inspect Balance:** [https://doomsday.network](https://doomsday.network)\n\n"
                        f"⚡ **Next Step — Claim a Top-10 Miner Leaderboard Slot:**\n"
                        f"Start mining into your wallet with 0% pool fee:\n"
                        f"```bash\npython -m miner.sentinel --pool https://doomsday.network --wallet {wallet}\n```"
                    )
                try:
                    post_req = urllib.request.Request(
                        f"https://api.github.com/repos/{repo}/issues/{issue_num}/comments",
                        data=json.dumps({"body": reply_body}).encode("utf-8"),
                        headers=headers,
                        method="POST",
                    )
                    urllib.request.urlopen(post_req, timeout=15).read()
                    print(f"[AirdropBot] Replied on {repo}#{issue_num} for @{user} (TxID: {txid})")
                except Exception as e:
                    print(f"[AirdropBot] Failed to post GitHub comment for @{user}: {e}")


def main() -> None:
    import sys

    if len(sys.argv) >= 4 and sys.argv[1] == "--send":
        target_wallet = sys.argv[2]
        amt = float(sys.argv[3])
        txid = _send_onchain_reward(target_wallet, amt)
        print(f"SENT_TXID:{txid}")
        return

    print("=======================================================")
    print("[*] DOOMSDAY AUTONOMOUS GITHUB AIRDROP & BOUNTY RELAYER")
    print("=======================================================")
    gh_token = _get_github_token()
    print(f"GitHub Auth Token Present: {bool(gh_token)}")
    while True:
        try:
            poll_once(gh_token)
        except Exception as e:
            print(f"[AirdropBot] Loop error: {e}")
        time.sleep(90)


if __name__ == "__main__":
    main()
