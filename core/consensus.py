import math
from typing import Dict, Tuple, List, Set, Optional
from core.crypto import bits_to_target, target_to_bits, MAX_TARGET, INITIAL_BITS
from core.transaction import Transaction, COIN, TxInput
from core.block import Block, calculate_merkle_root

TARGET_BLOCK_TIME = 20  # 20 seconds per block
HALVING_INTERVAL = 210_000  # Halving every 210,000 blocks (50 * 210,000 * 2 = 21,000,000 DOOM max supply)
INITIAL_REWARD_SPARKS = 50 * COIN
ASERT_HALF_LIFE = 240  # 4 minutes smoothing factor (12 blocks)


def get_block_reward(height: int) -> int:
    """Calculate mining subsidy for given block height with halving schedule."""
    halvings = height // HALVING_INTERVAL
    if halvings >= 64:
        return 0
    return INITIAL_REWARD_SPARKS >> halvings


def calculate_next_bits(prev_block: Block, anchor_block: Block, current_timestamp: Optional[int] = None) -> int:
    """
    ASERT (Absolutely Scheduled Exponentially-Rising Targets) per-block retargeting.
    
    Adjusts difficulty target smoothly per block based on time drift from expected schedule:
    Target_next = Target_anchor * 2^((t - t_anchor - (h - h_anchor) * T) / tau)
    """
    if prev_block.height < 1:
        return INITIAL_BITS

    effective_ts = current_timestamp if current_timestamp is not None else prev_block.header.timestamp
    effective_height = prev_block.height + (1 if current_timestamp is not None else 0)

    time_delta = effective_ts - anchor_block.header.timestamp
    height_delta = effective_height - anchor_block.height
    expected_time = height_delta * TARGET_BLOCK_TIME

    # Drift in seconds ahead or behind schedule
    drift = time_delta - expected_time

    # Exponent for smooth 2^(drift / half_life)
    exponent = drift / float(ASERT_HALF_LIFE)

    # Bound exponent: allow up to 256x difficulty increase (-8.0) against mega-miner bursts,
    # and up to 65536x relaxation (+16.0, clamped to MAX_TARGET) when idle rigs pause.
    exponent = max(-8.0, min(16.0, exponent))

    anchor_target = bits_to_target(anchor_block.header.bits)
    factor = math.pow(2.0, exponent)
    next_target = int(anchor_target * factor)

    # Clamp target to safe bounds
    if next_target > MAX_TARGET:
        next_target = MAX_TARGET
    elif next_target < 1:
        next_target = 1

    return target_to_bits(next_target)


def validate_transaction(tx: Transaction, utxo_set: Dict[str, Tuple[str, int]]) -> bool:
    """
    Validate a standard non-coinbase transaction against current UTXO state.
    UTXO set maps f"{txid}:{vout}" -> (recipient_address, amount_sparks)
    """
    if tx.is_coinbase:
        return len(tx.outputs) > 0 and all(o.amount > 0 for o in tx.outputs)

    if not tx.inputs or not tx.outputs:
        return False

    if any(out.amount <= 0 for out in tx.outputs):
        return False

    if tx.txid != tx.calculate_txid():
        return False

    from cryptography.hazmat.primitives.asymmetric import ec
    from core.crypto import public_key_to_address, verify_signature

    total_in = 0
    spent_keys: Set[str] = set()

    for idx, inp in enumerate(tx.inputs):
        key = f"{inp.txid}:{inp.vout}"
        if key in spent_keys:
            return False  # Double spending within same transaction
        spent_keys.add(key)

        if key not in utxo_set:
            return False  # Input does not exist or already spent

        owner_addr, amount = utxo_set[key]
        total_in += amount

        # Verify ECDSA signature and public key ownership
        if not inp.signature or not inp.pubkey_hex:
            return False

        try:
            pub_bytes = bytes.fromhex(inp.pubkey_hex)
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), pub_bytes)
            derived_addr = public_key_to_address(public_key)
            if derived_addr != owner_addr:
                return False
            sig_bytes = bytes.fromhex(inp.signature)
            signing_msg = tx.get_signing_bytes(idx)
            if not verify_signature(public_key, sig_bytes, signing_msg):
                return False
        except Exception:
            return False

    total_out = sum(out.amount for out in tx.outputs)
    if total_out > total_in:
        return False  # Inflation violation

    return True


def validate_block(
    block: Block,
    prev_block: Optional[Block],
    utxo_set: Dict[str, Tuple[str, int]],
    expected_bits: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Perform comprehensive validation of a proposed block according to consensus rules.
    """
    # 1. Verify Hash Integrity
    computed_hash = block.header.calculate_hash()
    if block.hash != computed_hash:
        return False, f"Invalid block hash: header hashes to {computed_hash}, claimed {block.hash}"

    # 2. Verify Proof-of-Work Target
    target = bits_to_target(block.header.bits)
    if int(block.hash, 16) >= target:
        return False, f"Block hash {block.hash} does not satisfy target {hex(target)}"

    # 3. Check Target Bits against Consensus
    if expected_bits is not None and block.header.bits != expected_bits:
        return False, f"Incorrect difficulty bits: claimed {hex(block.header.bits)}, expected {hex(expected_bits)}"

    # 4. Check Sequence & Timestamp
    if prev_block is not None:
        if block.height != prev_block.height + 1:
            return False, f"Invalid height: expected {prev_block.height + 1}, got {block.height}"
        if block.header.prev_hash != prev_block.hash:
            return False, f"Broken chain: prev_hash does not match parent block"
        if block.header.timestamp <= prev_block.header.timestamp:
            return False, "Block timestamp must be greater than parent timestamp"
        import time as _time
        if block.header.timestamp > int(_time.time()) + 60:
            return False, "Block timestamp is too far in the future (max +60s drift allowed)"

    # 5. Check Merkle Root
    merkle = calculate_merkle_root(block.transactions)
    if merkle != block.header.merkle_root:
        return False, f"Merkle root mismatch: computed {merkle}, claimed {block.header.merkle_root}"

    # 6. Check Coinbase Transaction
    if not block.transactions or not block.transactions[0].is_coinbase:
        return False, "First transaction must be a valid Coinbase transaction"

    coinbase = block.transactions[0]
    expected_subsidy = get_block_reward(block.height)

    # Calculate total transaction fees collected in this block
    tx_fees = 0
    temp_utxos = dict(utxo_set)
    for tx in block.transactions[1:]:
        if not validate_transaction(tx, temp_utxos):
            return False, f"Invalid transaction {tx.txid} in block"
        
        # Spend inputs
        t_in = sum(temp_utxos[f"{i.txid}:{i.vout}"][1] for i in tx.inputs)
        t_out = sum(o.amount for o in tx.outputs)
        tx_fees += (t_in - t_out)
        for i in tx.inputs:
            del temp_utxos[f"{i.txid}:{i.vout}"]
        for vout, o in enumerate(tx.outputs):
            temp_utxos[f"{tx.txid}:{vout}"] = (o.recipient, o.amount)

    coinbase_payout = sum(out.amount for out in coinbase.outputs)
    if coinbase_payout > (expected_subsidy + tx_fees):
        return False, f"Coinbase payout {coinbase_payout} exceeds allowed subsidy {expected_subsidy} + fees {tx_fees}"

    return True, "Valid"
