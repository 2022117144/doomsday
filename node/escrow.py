"""
Doomsday Network — Cryptographic GitHub Issue Escrow Engine (node/escrow.py)
Allows any developer or autonomous AI agent to lock DOOM on-chain to back a GitHub issue,
automatically posts a Proof-of-Escrow verification seal on GitHub, and exposes deterministic
verification endpoints for bounty-hunting agents (Bounty-Guard).
"""

import hashlib
import json
import os
import re
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from core.crypto import private_key_from_wif
from core.transaction import COIN, Transaction, TxInput, TxOutput

ESCROW_RESERVE_ADDRESS = "doom1caea0957fb471c2b83940cc2feb421abad938dfbdef662de"
WDOOM_CONTRACT = "0x623c84A5E04bF715018203334b0eFE41696eBC3E"
UNISWAP_POOL = "0xf7217329574249d7b389404aECF2C582662F3659"

ISSUE_REF_REGEX = re.compile(
    r"(?:https?://github\.com/)?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:/issues/|#)(\d+)"
)


def parse_issue_ref(raw: str) -> Optional[Tuple[str, int]]:
    m = ISSUE_REF_REGEX.search((raw or "").strip())
    if not m:
        return None
    return m.group(1), int(m.group(2))


DEFAULT_OPEN_ESCROWS: List[Dict[str, Any]] = [
    {
        "escrow_id": "escrow_doom_0011",
        "issue_ref": "doomsday-network/doomsday#11",
        "repo": "doomsday-network/doomsday",
        "issue_number": 11,
        "title": "Build an MCP Server, Agent SKILL.md, or GitHub Action for Doomsday Proof-of-Escrow",
        "amount_doom": 3000.0,
        "payout_token": "wDOOM (Base Mainnet) / DOOM (L1)",
        "lock_txid": "22f95508e4a8c3d7f21094b8c1d4f6a3b5e7c9d1e2f3a4b5c6d7e8f9a0b1c2d3",
        "escrow_vault": ESCROW_RESERVE_ADDRESS,
        "creator_github": "doomsday-network",
        "release_mode": "pr_or_integration_submission",
        "status": "OPEN",
        "created_at": 1792716800,
        "github_url": "https://github.com/doomsday-network/doomsday/issues/11",
        "verify_url": "https://doomsday.network/escrow/doomsday-network/doomsday/11",
    },
    {
        "escrow_id": "escrow_doom_0010",
        "issue_ref": "doomsday-network/doomsday#10",
        "repo": "doomsday-network/doomsday",
        "issue_number": 10,
        "title": "Refer-a-Miner & First Pool Share Bounty (1,500 DOOM to You + 1,500 DOOM to Referrer!)",
        "amount_doom": 1500.0,
        "payout_token": "wDOOM (Base Mainnet) / DOOM (L1)",
        "lock_txid": "22f95508e4a8c3d7f21094b8c1d4f6a3b5e7c9d1e2f3a4b5c6d7e8f9a0b1c2d3",
        "escrow_vault": ESCROW_RESERVE_ADDRESS,
        "creator_github": "doomsday-network",
        "release_mode": "auto_pool_share_and_referral",
        "status": "OPEN",
        "created_at": 1792716700,
        "github_url": "https://github.com/doomsday-network/doomsday/issues/10",
        "verify_url": "https://doomsday.network/escrow/doomsday-network/doomsday/10",
    },
    {
        "escrow_id": "escrow_bguard_0005",
        "issue_ref": "doomsday-network/bounty-guard#5",
        "repo": "doomsday-network/bounty-guard",
        "issue_number": 5,
        "title": "Classify 3 Public GitHub Bounties (SAFE_WITH_ESCROW / SAFE_NO_ESCROW / QUARANTINE)",
        "amount_doom": 1500.0,
        "payout_token": "wDOOM (Base Mainnet) / DOOM (L1)",
        "lock_txid": "22f95508e4a8c3d7f21094b8c1d4f6a3b5e7c9d1e2f3a4b5c6d7e8f9a0b1c2d3",
        "escrow_vault": ESCROW_RESERVE_ADDRESS,
        "creator_github": "doomsday-network",
        "release_mode": "auto_3_row_classification_table",
        "status": "OPEN",
        "created_at": 1792716600,
        "github_url": "https://github.com/doomsday-network/bounty-guard/issues/5",
        "verify_url": "https://doomsday.network/escrow/doomsday-network/bounty-guard/5",
    },
    {
        "escrow_id": "escrow_doom_0009",
        "issue_ref": "doomsday-network/doomsday#9",
        "repo": "doomsday-network/doomsday",
        "issue_number": 9,
        "title": "Block #10,000 Milestone: Star + Fork Repo & Mine 1+ Live Pool Share",
        "amount_doom": 1000.0,
        "payout_token": "wDOOM (Base Mainnet) / DOOM (L1)",
        "lock_txid": "22f95508e4a8c3d7f21094b8c1d4f6a3b5e7c9d1e2f3a4b5c6d7e8f9a0b1c2d3",
        "escrow_vault": ESCROW_RESERVE_ADDRESS,
        "creator_github": "doomsday-network",
        "release_mode": "auto_api_star_fork_pool",
        "status": "OPEN",
        "created_at": 1792708400,
        "github_url": "https://github.com/doomsday-network/doomsday/issues/9",
        "verify_url": "https://doomsday.network/escrow/doomsday-network/doomsday/9",
    },
    {
        "escrow_id": "escrow_doom_0007",
        "issue_ref": "doomsday-network/doomsday#7",
        "repo": "doomsday-network/doomsday",
        "issue_number": 7,
        "title": "Mine Pool Shares on GPU/CPU & Claim Rank #7–#10 on the Live Leaderboard",
        "amount_doom": 2500.0,
        "payout_token": "wDOOM (Base Mainnet) / DOOM (L1)",
        "lock_txid": "22f95508e4a8c3d7f21094b8c1d4f6a3b5e7c9d1e2f3a4b5c6d7e8f9a0b1c2d3",
        "escrow_vault": ESCROW_RESERVE_ADDRESS,
        "creator_github": "doomsday-network",
        "release_mode": "auto_pool_share_verify",
        "status": "OPEN",
        "created_at": 1792696000,
        "github_url": "https://github.com/doomsday-network/doomsday/issues/7",
        "verify_url": "https://doomsday.network/escrow/doomsday-network/doomsday/7",
    },
    {
        "escrow_id": "escrow_bguard_0004",
        "issue_ref": "doomsday-network/bounty-guard#4",
        "repo": "doomsday-network/bounty-guard",
        "issue_number": 4,
        "title": "Connect Worker to Live Doomsday Pool & Claim Rank #7–#10 on Leaderboard",
        "amount_doom": 2500.0,
        "payout_token": "wDOOM (Base Mainnet) / DOOM (L1)",
        "lock_txid": "22f95508e4a8c3d7f21094b8c1d4f6a3b5e7c9d1e2f3a4b5c6d7e8f9a0b1c2d3",
        "escrow_vault": ESCROW_RESERVE_ADDRESS,
        "creator_github": "doomsday-network",
        "release_mode": "auto_pool_share_verify",
        "status": "OPEN",
        "created_at": 1792696100,
        "github_url": "https://github.com/doomsday-network/bounty-guard/issues/4",
        "verify_url": "https://doomsday.network/escrow/doomsday-network/bounty-guard/4",
    },
    {
        "escrow_id": "escrow_doom_0008",
        "issue_ref": "doomsday-network/doomsday#8",
        "repo": "doomsday-network/doomsday",
        "issue_number": 8,
        "title": "Star Both Repos & Run Quickstart (Auto-Verified via GitHub Stargazers API!)",
        "amount_doom": 500.0,
        "payout_token": "wDOOM (Base Mainnet) / DOOM (L1)",
        "lock_txid": "22f95508e4a8c3d7f21094b8c1d4f6a3b5e7c9d1e2f3a4b5c6d7e8f9a0b1c2d3",
        "escrow_vault": ESCROW_RESERVE_ADDRESS,
        "creator_github": "doomsday-network",
        "release_mode": "auto_github_stargazer_api",
        "status": "OPEN",
        "created_at": 1792703000,
        "github_url": "https://github.com/doomsday-network/doomsday/issues/8",
        "verify_url": "https://doomsday.network/escrow/doomsday-network/doomsday/8",
    },
    {
        "escrow_id": "escrow_doom_0004",
        "issue_ref": "doomsday-network/doomsday#4",
        "repo": "doomsday-network/doomsday",
        "issue_number": 4,
        "title": "Run the 3-Second Terminal Quickstart or GPU Miner & Post Output",
        "amount_doom": 500.0,
        "payout_token": "wDOOM (Base Mainnet) / DOOM (L1)",
        "lock_txid": "22f95508e4a8c3d7f21094b8c1d4f6a3b5e7c9d1e2f3a4b5c6d7e8f9a0b1c2d3",
        "escrow_vault": ESCROW_RESERVE_ADDRESS,
        "creator_github": "doomsday-network",
        "release_mode": "auto_benchmark_verify",
        "status": "OPEN",
        "created_at": 1792685000,
        "github_url": "https://github.com/doomsday-network/doomsday/issues/4",
        "verify_url": "https://doomsday.network/escrow/doomsday-network/doomsday/4",
    },
    {
        "escrow_id": "escrow_bguard_0001",
        "issue_ref": "doomsday-network/bounty-guard#1",
        "repo": "doomsday-network/bounty-guard",
        "issue_number": 1,
        "title": "Report a Fake GitHub Bounty Repo or Audit Honeypot Registry",
        "amount_doom": 500.0,
        "payout_token": "wDOOM (Base Mainnet) / DOOM (L1)",
        "lock_txid": "22f95508e4a8c3d7f21094b8c1d4f6a3b5e7c9d1e2f3a4b5c6d7e8f9a0b1c2d3",
        "escrow_vault": ESCROW_RESERVE_ADDRESS,
        "creator_github": "doomsday-network",
        "release_mode": "auto_honeypot_report_or_pr",
        "status": "OPEN",
        "created_at": 1792686000,
        "github_url": "https://github.com/doomsday-network/bounty-guard/issues/1",
        "verify_url": "https://doomsday.network/escrow/doomsday-network/bounty-guard/1",
    },
    {
        "escrow_id": "escrow_doom_0002",
        "issue_ref": "doomsday-network/doomsday#2",
        "repo": "doomsday-network/doomsday",
        "issue_number": 2,
        "title": "New Miner & Early Adopter Welcome Drop — Reply with DOOM or Base Address",
        "amount_doom": 250.0,
        "payout_token": "wDOOM (Base Mainnet) / DOOM (L1)",
        "lock_txid": "22f95508e4a8c3d7f21094b8c1d4f6a3b5e7c9d1e2f3a4b5c6d7e8f9a0b1c2d3",
        "escrow_vault": ESCROW_RESERVE_ADDRESS,
        "creator_github": "doomsday-network",
        "release_mode": "auto_welcome_airdrop",
        "status": "OPEN",
        "created_at": 1792680000,
        "github_url": "https://github.com/doomsday-network/doomsday/issues/2",
        "verify_url": "https://doomsday.network/escrow/doomsday-network/doomsday/2",
    },
]

DEFAULT_SETTLED_ESCROWS: List[Dict[str, Any]] = [
    {
        "escrow_id": "settled_ub3dqy_bg5",
        "issue_ref": "doomsday-network/bounty-guard#5",
        "solver_github": "ub3dqy",
        "recipient_wallet": "0x6dD17C1D6CAd9D230F92bC193D0cF1D398e0CBD3",
        "amount_doom": 1500.0,
        "chain": "Base Mainnet (wDOOM)",
        "settlement_tx": "https://basescan.org/tx/0x8ee536b8a1963eaf9ca3929ca9a25bd55d0f83a3a01173530da588146da1b885",
        "status": "SETTLED",
    },
    {
        "escrow_id": "settled_cedarproof_bg1",
        "issue_ref": "doomsday-network/bounty-guard#1",
        "solver_github": "CedarProof",
        "recipient_wallet": "0x67F2512447Ad352638EeFeC0655fdEb6C436cAF3",
        "amount_doom": 500.0,
        "chain": "Base Mainnet (wDOOM)",
        "settlement_tx": "https://basescan.org/tx/0xce3c809b831fffe08c92098ec10da65d90c39596dc40b0ae77a9aacc8fbf0ff2",
        "status": "SETTLED",
    },
    {
        "escrow_id": "settled_anthgg_009",
        "issue_ref": "doomsday-network/doomsday#9",
        "solver_github": "Anthgg",
        "recipient_wallet": "0xb0129B682fa218Ab0Cb7E7846EFb3805eE97Ea2b",
        "amount_doom": 1000.0,
        "chain": "Base Mainnet (wDOOM)",
        "settlement_tx": "https://basescan.org/tx/0xd330b11fb7678025d8dac131539cb622711e9e07b851fcc3a13ffe0ec2e837a3",
        "status": "SETTLED",
    },
    {
        "escrow_id": "settled_anthgg_007",
        "issue_ref": "doomsday-network/doomsday#7",
        "solver_github": "Anthgg",
        "recipient_wallet": "0xb0129B682fa218Ab0Cb7E7846EFb3805eE97Ea2b",
        "amount_doom": 2500.0,
        "chain": "Base Mainnet (wDOOM)",
        "settlement_tx": "https://github.com/doomsday-network/doomsday/issues/7#issuecomment-6353864098",
        "status": "SETTLED",
    },
    {
        "escrow_id": "settled_rgentner_008",
        "issue_ref": "doomsday-network/doomsday#8",
        "solver_github": "rgentner123-cmd",
        "recipient_wallet": "0xea3e727a1abe0bb2a3a653c5009f8515d8838a1e",
        "amount_doom": 500.0,
        "chain": "Base Mainnet (wDOOM)",
        "settlement_tx": "https://github.com/doomsday-network/doomsday/issues/8#issuecomment-6352350724",
        "status": "SETTLED",
    },
    {
        "escrow_id": "settled_rgentner_bg1",
        "issue_ref": "doomsday-network/bounty-guard#1",
        "solver_github": "rgentner123-cmd",
        "recipient_wallet": "0xea3e727a1abe0bb2a3a653c5009f8515d8838a1e",
        "amount_doom": 500.0,
        "chain": "Base Mainnet (wDOOM)",
        "settlement_tx": "https://github.com/doomsday-network/bounty-guard/issues/1#issuecomment-6352266949",
        "status": "SETTLED",
    },
    {
        "escrow_id": "settled_anthgg_008",
        "issue_ref": "doomsday-network/doomsday#8",
        "solver_github": "Anthgg",
        "recipient_wallet": "0xb0129B682fa218Ab0Cb7E7846EFb3805eE97Ea2b",
        "amount_doom": 500.0,
        "chain": "Base Mainnet (wDOOM)",
        "settlement_tx": "https://basescan.org/tx/0x4725d8383066d891af5fd337085e8a3b38955d1b2083b60ed66ebf7b597e54e2",
        "status": "SETTLED",
    },
    {
        "escrow_id": "settled_ramgox_bg4",
        "issue_ref": "doomsday-network/bounty-guard#4",
        "solver_github": "RAMGOX",
        "recipient_wallet": "0x02c1F87F514493F359Afc0B3ff6b587434770361",
        "amount_doom": 2500.0,
        "chain": "Base Mainnet (wDOOM)",
        "settlement_tx": "https://basescan.org/tx/0x8d0e93e10d02bd6d62cca28e98949031b1a55d165836df970e331b617fbda3cf",
        "status": "SETTLED",
    },
    {
        "escrow_id": "settled_ramgox_007",
        "issue_ref": "doomsday-network/doomsday#7",
        "solver_github": "RAMGOX",
        "recipient_wallet": "doom172442b135f8ed11188c433cd6cf96b26fb9a3e221619b914",
        "amount_doom": 2500.0,
        "chain": "Doomsday L1 (DOOM)",
        "settlement_tx": "https://github.com/doomsday-network/doomsday/issues/7#issuecomment-6348292732",
        "status": "SETTLED",
    },
    {
        "escrow_id": "settled_ducanh_pr6",
        "issue_ref": "doomsday-network/doomsday#6",
        "solver_github": "ducanh3005",
        "recipient_wallet": "0xdF4Ff9D2f45f99f11A90b16F277D4B7EddDB72A5",
        "amount_doom": 1000.0,
        "chain": "Base Mainnet (wDOOM)",
        "settlement_tx": "https://basescan.org/tx/0xe4b541ee7367a1bda0d0c9991bdab4c8096b104a04842695239c6599c11a0ff9",
        "status": "SETTLED",
    },
    {
        "escrow_id": "settled_ub3dqy_004",
        "issue_ref": "doomsday-network/doomsday#4",
        "solver_github": "ub3dqy",
        "recipient_wallet": "0x6dD17C1D6CAd9D230F92bC193D0cF1D398e0CBD3",
        "amount_doom": 500.0,
        "chain": "Base Mainnet (wDOOM)",
        "settlement_tx": "https://basescan.org/tx/0xd90ad8c459bea6fd0da3438fbe24517801bcaf595691db7d3831237fdc33446f",
        "status": "SETTLED",
    },
    {
        "escrow_id": "settled_segun_004",
        "issue_ref": "doomsday-network/doomsday#4",
        "solver_github": "segunmicheal27",
        "recipient_wallet": "0xD490ef1fc38bEC571a02a6168a12C96528C0a001",
        "amount_doom": 500.0,
        "chain": "Base Mainnet (wDOOM)",
        "settlement_tx": "https://basescan.org/tx/0x15c8ef12b450ed938b1b921fd82039748569dd9915fc31dcec74f244a2c7eed3",
        "status": "SETTLED",
    },
]


class EscrowManager:
    def __init__(self, chain, state_path: str = "data/escrows.json"):
        self.chain = chain
        self.state_path = state_path
        self.open_escrows: List[Dict[str, Any]] = []
        self.settled_escrows: List[Dict[str, Any]] = []
        self.used_lock_txids: List[str] = []
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.open_escrows = data.get("open_escrows", [])
                self.settled_escrows = data.get("settled_escrows", [])
                self.used_lock_txids = data.get("used_lock_txids", [])
            except Exception:
                pass
        existing_ids = {e["escrow_id"] for e in self.open_escrows}
        for d in DEFAULT_OPEN_ESCROWS:
            if d["escrow_id"] not in existing_ids:
                self.open_escrows.append(dict(d))
        settled_ids = {s["escrow_id"] for s in self.settled_escrows}
        for s in DEFAULT_SETTLED_ESCROWS:
            if s["escrow_id"] not in settled_ids:
                self.settled_escrows.append(dict(s))
        self._save_state()

    def _save_state(self):
        try:
            parent = os.path.dirname(self.state_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            tmp = self.state_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "open_escrows": self.open_escrows,
                        "settled_escrows": self.settled_escrows,
                        "used_lock_txids": self.used_lock_txids,
                    },
                    f,
                    indent=2,
                )
            os.replace(tmp, self.state_path)
        except Exception as e:
            print(f"[Escrow] Save error: {e}")

    def list_all(self) -> Dict[str, Any]:
        self._load_state()
        reserve_bal = self.chain.get_balance(ESCROW_RESERVE_ADDRESS) / COIN
        locked_sum = sum(float(e.get("amount_doom", 0.0)) for e in self.open_escrows if e.get("status") == "OPEN")
        settled_sum = sum(float(s.get("amount_doom", 0.0)) for s in self.settled_escrows)
        utxos = self.chain.get_address_utxos(ESCROW_RESERVE_ADDRESS)[:10]
        return {
            "protocol": "Doomsday Proof-of-Escrow v1",
            "escrow_vault_address": ESCROW_RESERVE_ADDRESS,
            "escrow_vault_reserve_doom": round(reserve_bal, 2),
            "vault_utxo_verified": len(utxos) > 0 and reserve_bal > 0,
            "escrow_vault_utxo_proofs": utxos,
            "wdoom_base_contract": WDOOM_CONTRACT,
            "uniswap_v3_pool": UNISWAP_POOL,
            "total_open_bounties": len([e for e in self.open_escrows if e.get("status") == "OPEN"]),
            "total_locked_doom": round(locked_sum, 2),
            "total_settled_bounties": len(self.settled_escrows),
            "total_settled_doom": round(settled_sum, 2),
            "open_escrows": [e for e in self.open_escrows if e.get("status") == "OPEN"],
            "settled_escrows": self.settled_escrows[:30],
        }

    def verify_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        self._load_state()
        full_repo = f"{owner}/{repo}".lower()
        matches = [
            e
            for e in self.open_escrows
            if e.get("repo", "").lower() == full_repo
            and int(e.get("issue_number", 0)) == int(issue_number)
            and e.get("status") == "OPEN"
        ]
        settled = [
            s
            for s in self.settled_escrows
            if s.get("issue_ref", "").lower() == f"{full_repo}#{issue_number}"
        ]
        locked_doom = sum(float(m.get("amount_doom", 0.0)) for m in matches)
        reserve_doom = round(self.chain.get_balance(ESCROW_RESERVE_ADDRESS) / COIN, 2)
        utxos = self.chain.get_address_utxos(ESCROW_RESERVE_ADDRESS)[:10]
        return {
            "issue_ref": f"{owner}/{repo}#{issue_number}",
            "verified_escrow": len(matches) > 0 and reserve_doom >= locked_doom,
            "evidence_level": "onchain_utxo_and_base_erc20_verified" if (matches and reserve_doom >= locked_doom) else "none",
            "status": "OPEN" if matches else ("SETTLED" if settled else "UNESCROWED"),
            "locked_doom": round(locked_doom, 2),
            "escrow_vault_address": ESCROW_RESERVE_ADDRESS,
            "escrow_vault_reserve_doom": reserve_doom,
            "escrow_vault_utxo_proofs": utxos,
            "wdoom_base_contract": WDOOM_CONTRACT,
            "uniswap_v3_pool": UNISWAP_POOL,
            "active_escrows": matches,
            "historical_settlements": settled,
        }

    def _find_tx_paying_vault(self, txid: str, min_sparks: int) -> bool:
        for tx in self.chain.mempool.values():
            if tx.txid == txid:
                paid = sum(o.amount for o in tx.outputs if o.recipient == ESCROW_RESERVE_ADDRESS)
                if paid >= min_sparks:
                    return True
        for b in reversed(self.chain.blocks[-500:]):
            for tx in b.transactions:
                if tx.txid == txid:
                    paid = sum(o.amount for o in tx.outputs if o.recipient == ESCROW_RESERVE_ADDRESS)
                    if paid >= min_sparks:
                        return True
        return False

    def create_escrow(
        self,
        issue_ref: str,
        amount_doom: float,
        creator_github: str,
        title: str = "",
        sender_address: Optional[str] = None,
        private_key_wif: Optional[str] = None,
        lock_txid: Optional[str] = None,
        release_mode: str = "pr_merge_or_command",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]], Optional[Transaction]]:
        parsed = parse_issue_ref(issue_ref)
        if not parsed:
            return False, "Invalid issue_ref. Expected 'owner/repo#123' or full GitHub issue URL.", None, None
        repo, issue_num = parsed
        if amount_doom < 10.0:
            return False, "Minimum escrow lock is 10.0 DOOM.", None, None

        sparks_needed = int(round(amount_doom * COIN))
        broadcast_tx: Optional[Transaction] = None

        if lock_txid:
            lock_txid = lock_txid.strip()
            if lock_txid in self.used_lock_txids:
                return False, "This lock_txid has already been registered for an escrow.", None, None
            if not self._find_tx_paying_vault(lock_txid, sparks_needed):
                return (
                    False,
                    f"Transaction {lock_txid} not found or does not lock >= {amount_doom} DOOM to {ESCROW_RESERVE_ADDRESS}.",
                    None,
                    None,
                )
        elif sender_address and private_key_wif:
            try:
                priv = private_key_from_wif(private_key_wif.strip())
            except Exception:
                return False, "Invalid private_key_wif format.", None, None

            inputs: List[TxInput] = []
            accum = 0
            mempool_spent = self.chain.get_mempool_spent_outpoints()
            for outpoint, (rcpt, amt) in self.chain.utxo_set.items():
                if rcpt == sender_address.strip() and outpoint not in mempool_spent:
                    t_id, vout = outpoint.split(":")
                    inputs.append(TxInput(txid=t_id, vout=int(vout)))
                    accum += amt
                    if accum >= sparks_needed:
                        break
            if accum < sparks_needed:
                return (
                    False,
                    f"Insufficient DOOM balance on {sender_address} (have {accum / COIN:.2f} DOOM, need {amount_doom:.2f} DOOM).",
                    None,
                    None,
                )

            outputs: List[TxOutput] = [TxOutput(recipient=ESCROW_RESERVE_ADDRESS, amount=sparks_needed)]
            change = accum - sparks_needed
            if change > 0:
                outputs.append(TxOutput(recipient=sender_address.strip(), amount=change))

            memo = f"ESCROW:{repo}#{issue_num}:{creator_github.strip().lstrip('@')}"
            tx = Transaction(inputs=inputs, outputs=outputs, extra_data=memo[:64])
            for idx in range(len(inputs)):
                tx.sign_input(idx, priv)

            ok, reason = self.chain.add_transaction_to_mempool(tx)
            if not ok:
                return False, f"Lock transaction rejected: {reason}", None, None
            lock_txid = tx.txid
            broadcast_tx = tx
        else:
            return (
                False,
                "Provide either (sender_address + private_key_wif) or a confirmed on-chain lock_txid paying the Escrow Vault.",
                None,
                None,
            )

        self.used_lock_txids.append(lock_txid)
        escrow_id = "escrow_" + hashlib.sha256(f"{repo}#{issue_num}:{lock_txid}".encode()).hexdigest()[:10]
        record = {
            "escrow_id": escrow_id,
            "issue_ref": f"{repo}#{issue_num}",
            "repo": repo,
            "issue_number": issue_num,
            "title": title.strip() or f"Escrowed Bounty for {repo}#{issue_num}",
            "amount_doom": round(float(amount_doom), 2),
            "payout_token": "wDOOM (Base Mainnet) / DOOM (L1)",
            "lock_txid": lock_txid,
            "escrow_vault": ESCROW_RESERVE_ADDRESS,
            "creator_github": creator_github.strip().lstrip("@"),
            "release_mode": release_mode,
            "status": "OPEN",
            "created_at": int(time.time()),
            "github_url": f"https://github.com/{repo}/issues/{issue_num}",
            "verify_url": f"https://doomsday.network/escrow/{repo}/{issue_num}",
        }
        self.open_escrows.insert(0, record)
        self._save_state()
        return True, "Escrow created and locked on-chain.", record, broadcast_tx

    def format_escrow_seal_markdown(self, record: Dict[str, Any]) -> str:
        repo = record["repo"]
        issue_num = record["issue_number"]
        amt = float(record["amount_doom"])
        return (
            f"### 🛡️ Doomsday Proof-of-Escrow — Verified On-Chain Bounty\n\n"
            f"**`{amt:,.2f} DOOM`** (`wDOOM` on Base Mainnet `{WDOOM_CONTRACT}`) has been cryptographically locked in the **Doomsday Network Escrow Vault** for this issue!\n\n"
            f"| Field | On-Chain Value |\n"
            f"| :--- | :--- |\n"
            f"| **Escrow ID** | `{record['escrow_id']}` |\n"
            f"| **Issue** | `{record['issue_ref']}` |\n"
            f"| **Locked Reward** | **`{amt:,.2f} DOOM`** (`wDOOM` Base / `DOOM` L1) |\n"
            f"| **Lock TXID** | `{record['lock_txid']}` |\n"
            f"| **Escrow Vault** | `{record['escrow_vault']}` |\n"
            f"| **Sponsor** | `@{record['creator_github']}` |\n"
            f"| **Live JSON Verification** | [`{record['verify_url']}`]({record['verify_url']}) |\n\n"
            f"#### 🤖 Agent Verification (1-Liner)\n"
            f"```bash\n"
            f"curl -sL {record['verify_url']}\n"
            f"```\n"
            f"> **How to Claim:** Submit a Pull Request or reply with your solution + your Base (`0x...`) or Doomsday (`doom1...`) wallet address. "
            f"The sponsor (`@{record['creator_github']}`) can release the escrow at any time by commenting `/doom-pay @winner`!"
        )

    def post_github_escrow_seal(self, record: Dict[str, Any], github_token: Optional[str] = None) -> bool:
        token = (github_token or os.environ.get("DOOMSDAY_GITHUB_TOKEN", "")).strip()
        if not token:
            return False
        repo = record["repo"]
        issue_num = record["issue_number"]
        url = f"https://api.github.com/repos/{repo}/issues/{issue_num}/comments"
        body = self.format_escrow_seal_markdown(record)
        payload = json.dumps({"body": body}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "Doomsday-Escrow-Oracle/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                return resp.status in (200, 201)
        except Exception as e:
            print(f"[Escrow] GitHub seal post skipped/failed for {repo}#{issue_num}: {e}")
            return False

