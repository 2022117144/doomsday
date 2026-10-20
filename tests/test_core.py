import time
from core.crypto import generate_keypair, public_key_to_address, bits_to_target
from core.transaction import create_coinbase_tx, Transaction, TxInput, TxOutput, COIN
from core.block import create_genesis_block, Block, BlockHeader, calculate_merkle_root
from core.consensus import validate_block, validate_transaction, get_block_reward, calculate_next_bits, HALVING_INTERVAL

def test_core_flow():
    print("Generating keypair...")
    priv, pub = generate_keypair()
    addr = public_key_to_address(pub)
    print("Generated Address:", addr)
    assert addr.startswith("doom1")

    print("Building Genesis block...")
    genesis = create_genesis_block()
    print("Genesis Block Hash:", genesis.hash)
    print("Genesis Nonce:", genesis.header.nonce)
    print("Genesis Merkle Root:", genesis.header.merkle_root)

    # Validate Genesis block
    ok, msg = validate_block(genesis, None, {})
    assert ok, f"Genesis validation failed: {msg}"
    print("Genesis block successfully validated!")

    # Build Block #1
    reward = get_block_reward(1)
    assert reward == 50 * COIN
    cb1 = create_coinbase_tx(addr, reward, 1)
    merkle1 = calculate_merkle_root([cb1])
    bits1 = genesis.header.bits
    target1 = bits_to_target(bits1)

    h1 = BlockHeader(
        version=1,
        prev_hash=genesis.hash,
        merkle_root=merkle1,
        timestamp=genesis.header.timestamp + 20,
        bits=bits1,
        nonce=0,
        miner_address=addr
    )

    # Solve block 1
    prefix = h1.get_prefix_bytes()
    from core.crypto import doom_hash
    nonce = 0
    while True:
        h_bytes = doom_hash(prefix, nonce)
        if int.from_bytes(h_bytes, byteorder='big') < target1:
            h1.nonce = nonce
            break
        nonce += 1

    b1 = Block(h1, [cb1], height=1)
    print("Block #1 Hash:", b1.hash, "with nonce:", b1.header.nonce)

    # Validate Block #1
    utxo_set = {f"{genesis.transactions[0].txid}:0": (addr, 50 * COIN)}
    ok, msg = validate_block(b1, genesis, utxo_set, expected_bits=bits1)
    assert ok, f"Block 1 validation failed: {msg}"
    print("Block #1 validated successfully!")

    # Test difficulty retargeting
    next_bits = calculate_next_bits(b1, genesis)
    print("Next Bits calculated:", hex(next_bits))


def test_transaction_security_and_halving():
    # 1. Verify 21M supply schedule with 210,000 block halving interval
    assert HALVING_INTERVAL == 210_000
    assert get_block_reward(0) == 50 * COIN
    assert get_block_reward(209_999) == 50 * COIN
    assert get_block_reward(210_000) == 25 * COIN

    # 2. Verify cryptographic signature & ownership enforcement
    priv_alice, pub_alice = generate_keypair()
    addr_alice = public_key_to_address(pub_alice)

    priv_attacker, pub_attacker = generate_keypair()
    addr_attacker = public_key_to_address(pub_attacker)

    fake_txid = "a" * 64
    utxo_set = {f"{fake_txid}:0": (addr_alice, 10 * COIN)}

    # Legitimate transaction signed by Alice
    valid_tx = Transaction(
        inputs=[TxInput(txid=fake_txid, vout=0)],
        outputs=[TxOutput(recipient=addr_attacker, amount=5 * COIN), TxOutput(recipient=addr_alice, amount=5 * COIN)]
    )
    valid_tx.sign_input(0, priv_alice)
    assert validate_transaction(valid_tx, utxo_set) is True

    # Attacker tries to sign Alice's UTXO with attacker's key
    stolen_tx = Transaction(
        inputs=[TxInput(txid=fake_txid, vout=0)],
        outputs=[TxOutput(recipient=addr_attacker, amount=10 * COIN)]
    )
    stolen_tx.sign_input(0, priv_attacker)
    assert validate_transaction(stolen_tx, utxo_set) is False

    # Attacker tries to pass Alice's pubkey with a forged signature
    forged_tx = Transaction(
        inputs=[TxInput(txid=fake_txid, vout=0, signature="30440220" + "11" * 32 + "0220" + "22" * 32, pubkey_hex=valid_tx.inputs[0].pubkey_hex)],
        outputs=[TxOutput(recipient=addr_attacker, amount=10 * COIN)]
    )
    assert validate_transaction(forged_tx, utxo_set) is False

    # Negative output value inflation attack
    neg_tx = Transaction(
        inputs=[TxInput(txid=fake_txid, vout=0)],
        outputs=[TxOutput(recipient=addr_attacker, amount=100 * COIN), TxOutput(recipient=addr_alice, amount=-90 * COIN)]
    )
    neg_tx.sign_input(0, priv_alice)
    assert validate_transaction(neg_tx, utxo_set) is False


if __name__ == "__main__":
    test_core_flow()
    test_transaction_security_and_halving()
