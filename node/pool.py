import time
import math
import struct
import hashlib
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from core.crypto import bits_to_target, target_to_bits, doom_hash
from core.consensus import get_block_reward
from core.transaction import COIN

# Share difficulty: Easy enough for entry-level GPUs to submit shares regularly
# 0x1f00ffff = maximum target (1 hash on average)
# 0x1e0fffff = ~1 in 256 hashes
POOL_SHARE_BITS = 0x1e0fffff
POOL_SHARE_TARGET = bits_to_target(POOL_SHARE_BITS)


class PoolWorker:
    def __init__(self, address: str, name: str):
        self.address = address
        self.name = name
        self.shares = 0
        self.valid_shares_total = 0
        self.last_share_time = time.time()
        self.hashrate_mhs = 0.0


class MiningPool:
    def __init__(
        self,
        chain,
        pool_address: str = "doom1pool0000000000000000000000000000000000000",
        fee_pct: float = 0.0,
        state_path: str = "data/pool_state.json"
    ):
        self.chain = chain
        self.pool_address = pool_address
        self.fee_pct = fee_pct
        self.share_target = POOL_SHARE_TARGET
        self.state_path = state_path

        # Worker management: worker_key (address:name) -> PoolWorker
        self.workers: Dict[str, PoolWorker] = {}

        # Round accounting: worker_address -> round_shares
        self.round_shares: Dict[str, int] = {}

        # Balance accounting: worker_address -> unpaid_sparks
        self.unpaid_sparks: Dict[str, int] = {}
        self.total_paid_sparks: Dict[str, int] = {}

        # History of blocks solved by pool
        self.blocks_found: List[Dict[str, Any]] = []
        self._load_state()

    def _load_state(self):
        """Load persistent pool balances, round shares, and block history from disk."""
        if not self.state_path or not os.path.exists(self.state_path):
            return
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.round_shares = {k: int(v) for k, v in data.get("round_shares", {}).items()}
            self.unpaid_sparks = {k: int(v) for k, v in data.get("unpaid_sparks", {}).items()}
            self.total_paid_sparks = {k: int(v) for k, v in data.get("total_paid_sparks", {}).items()}
            self.blocks_found = list(data.get("blocks_found", []))
        except Exception as e:
            print(f"[Pool] Warning: Could not load pool state ({e})")

    def _save_state(self):
        """Atomically persist pool state to disk so balances survive node restarts."""
        if not self.state_path:
            return
        try:
            parent = os.path.dirname(self.state_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            tmp_path = self.state_path + ".tmp"
            payload = {
                "round_shares": self.round_shares,
                "unpaid_sparks": self.unpaid_sparks,
                "total_paid_sparks": self.total_paid_sparks,
                "blocks_found": self.blocks_found[-200:]
            }
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp_path, self.state_path)
        except Exception as e:
            print(f"[Pool] Warning: Failed to save pool state ({e})")

    def get_job(self, worker_address: str, worker_name: str = "Worker-Default") -> Dict[str, Any]:
        """Generate a pool mining job template with pool share target."""
        key = f"{worker_address}:{worker_name}"
        if key not in self.workers:
            self.workers[key] = PoolWorker(worker_address, worker_name)

        # Base block template is generated paying the pool address
        template = self.chain.create_block_template(self.pool_address)

        # Pool assigns its own share difficulty target to the worker
        share_target_high = (self.share_target >> 192) & 0xFFFFFFFFFFFFFFFF

        job = dict(template)
        job["pool_mode"] = True
        job["pool_address"] = self.pool_address
        job["worker_address"] = worker_address
        job["worker_name"] = worker_name
        job["network_target_high"] = template["target_high"]
        # Override target_high with share target so worker GPU submits shares
        job["target_high"] = share_target_high
        job["share_bits"] = POOL_SHARE_BITS
        return job

    def submit_share(
        self,
        height: int,
        nonce: int,
        worker_address: str,
        worker_name: str = "Worker-Default",
        timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verify a share submitted by a worker.
        If the share meets network target, commit the full block to the ledger.
        """
        now = time.time()
        key = f"{worker_address}:{worker_name}"
        if key not in self.workers:
            self.workers[key] = PoolWorker(worker_address, worker_name)
        worker = self.workers[key]

        # 0. Check for stale share
        tip = self.chain.get_tip()
        if height != tip.height + 1:
            return {"accepted": False, "reason": f"Stale share: height {height} != tip {tip.height + 1}"}

        # Retrieve template
        template = None
        if timestamp is not None and (self.pool_address, height, timestamp) in self.chain.active_templates:
            template = self.chain.active_templates[(self.pool_address, height, timestamp)]
        if template is None:
            template = self.chain.create_block_template(self.pool_address, timestamp=timestamp)

        prefix = bytes.fromhex(template["header_prefix_hex"])
        digest_bytes = doom_hash(prefix, nonce)
        computed_hash_int = int.from_bytes(digest_bytes, byteorder='big')
        hash_hex = digest_bytes.hex()

        # 1. Verify Share Target
        if computed_hash_int >= self.share_target:
            return {"accepted": False, "reason": "Hash does not satisfy share difficulty"}

        # Record share
        worker.shares += 1
        worker.valid_shares_total += 1
        self.round_shares[worker_address] = self.round_shares.get(worker_address, 0) + 1

        # Estimate worker hashrate from share interval
        dt = max(0.5, now - worker.last_share_time)
        worker.last_share_time = now
        # Expected hashes per share = 2^256 / share_target
        expected_hashes = (1 << 256) / float(self.share_target)
        inst_mhs = (expected_hashes / dt) / 1_000_000.0
        worker.hashrate_mhs = round((worker.hashrate_mhs * 0.7) + (inst_mhs * 0.3), 2)

        # 2. Check if Share satisfies Network Block Target!
        network_target = bits_to_target(template["bits"])
        block_solved = False
        block_hash = None

        if computed_hash_int < network_target:
            # Full Network Block Solved!
            ok, msg = self.chain.add_block_candidate(
                height=height,
                nonce=nonce,
                miner_address=self.pool_address,
                miner_name=f"Pool-[{worker_name}]",
                timestamp=timestamp
            )
            if ok:
                block_solved = True
                block_hash = hash_hex
                self._distribute_block_rewards(height, block_hash, worker_address)

        self._save_state()
        return {
            "accepted": True,
            "share_valid": True,
            "block_solved": block_solved,
            "block_hash": block_hash,
            "worker_shares": worker.shares
        }

    def _distribute_block_rewards(self, height: int, block_hash: str, solver_address: str):
        """Distribute block reward proportionally across all round contributors."""
        total_reward_sparks = get_block_reward(height)
        net_reward = int(total_reward_sparks * (1.0 - (self.fee_pct / 100.0)))
        total_round_shares = sum(self.round_shares.values())

        if total_round_shares == 0:
            total_round_shares = 1
            self.round_shares[solver_address] = 1

        # PPLNS / Proportional split
        payouts = {}
        for addr, shares in self.round_shares.items():
            pct = shares / float(total_round_shares)
            earned = int(net_reward * pct)
            self.unpaid_sparks[addr] = self.unpaid_sparks.get(addr, 0) + earned
            payouts[addr] = earned / COIN

        self.blocks_found.append({
            "height": height,
            "hash": block_hash,
            "solver": solver_address,
            "timestamp": int(time.time()),
            "total_shares": total_round_shares,
            "payouts_count": len(payouts)
        })

        # Reset round shares for the next block
        self.round_shares.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate pool statistics for frontend dashboard."""
        now = time.time()
        active_workers = [w for w in self.workers.values() if now - w.last_share_time < 60]
        total_mhs = sum(w.hashrate_mhs for w in active_workers)

        return {
            "pool_name": "Doomsday Sovereign Mining Pool",
            "pool_address": self.pool_address,
            "fee_percent": self.fee_pct,
            "active_miners": len(active_workers),
            "pool_hashrate_mhs": round(total_mhs, 2),
            "share_difficulty": hex(POOL_SHARE_BITS),
            "total_blocks_found": len(self.blocks_found),
            "recent_blocks": list(reversed(self.blocks_found[-10:])),
            "total_shares_round": sum(self.round_shares.values())
        }

    def get_worker_stats(self, address: str) -> Dict[str, Any]:
        """Get personal statistics and unpaid rewards for a worker address."""
        now = time.time()
        matching = [w for w in self.workers.values() if w.address == address]
        active = [w for w in matching if now - w.last_share_time < 60]
        total_mhs = sum(w.hashrate_mhs for w in active)
        unpaid = self.unpaid_sparks.get(address, 0)

        return {
            "address": address,
            "is_active": len(active) > 0,
            "active_rigs": len(active),
            "hashrate_mhs": round(total_mhs, 2),
            "round_shares": self.round_shares.get(address, 0),
            "unpaid_doom": unpaid / COIN,
            "total_paid_doom": self.total_paid_sparks.get(address, 0) / COIN
        }
