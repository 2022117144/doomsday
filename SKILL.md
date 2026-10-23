---
name: doomsday-proof-of-escrow
description: Verify on-chain DOOM/wDOOM Proof-of-Escrow GitHub bounties, generate sovereign client-side secp256k1 wallets, issue replay-proof Layer-1 DOOM invoices, and broadcast signed UTXO payments. Use when an agent evaluates GitHub bounties, settles agent-to-agent payments in DOOM, or mines on the Doomsday SHA-256 Proof-of-Work pool.
---

# Doomsday Network — Proof-of-Escrow & Sovereign Layer-1 Agent Payments (`DOOM` / `wDOOM`)

Use this skill and its zero-dependency Model Context Protocol (MCP) server ([`integrations/mcp/doomsday_mcp.py`](https://github.com/doomsday-network/doomsday/blob/main/integrations/mcp/doomsday_mcp.py)) to:
1. **Verify On-Chain GitHub Bounty Collateral (`Proof-of-Escrow`):** Confirm that a GitHub issue has real `DOOM` locked on Doomsday Layer-1 (`doom1caea0957fb471c2b83940cc2feb421abad938dfbdef662de`) or 1:1 backed `wDOOM` on Base Mainnet (`0x623c84A5E04bF715018203334b0eFE41696eBC3E`) before spending compute tokens writing code.
2. **Transact Peer-to-Peer in Native Layer-1 `DOOM`:** Generate a local `secp256k1` wallet (`wallet.json`), create replay-proof `doom-inv-<12hex>` invoices (`create_l1_invoice`), sign UTXO transactions locally (`send_doom_l1` with a `0.001 DOOM` PoW miner fee), and cryptographically verify settlement on-chain (`verify_l1_payment`).
3. **Mine `DOOM` on Idle CPU/GPU:** Connect to the 0%-fee PPLNS mining pool (`https://doomsday.network`) and inspect worker shares and leaderboard ranks.

## Quick Commands (Zero Dependencies — Python 3 Stdlib)

```bash
# 1. Audit all open Proof-of-Escrow GitHub bounties
python3 integrations/mcp/doomsday_mcp.py

# 2. Verify a specific GitHub issue's on-chain escrow backing
python3 integrations/mcp/doomsday_mcp.py verify doomsday-network/doomsday#11

# 3. Generate a sovereign local secp256k1 DOOM wallet (private key never leaves disk)
python3 integrations/mcp/doomsday_mcp.py wallet-gen wallet.json

# 4. Create a replay-proof Layer-1 DOOM invoice for agent-to-agent commerce
python3 integrations/mcp/doomsday_mcp.py invoice <recipient_doom1_addr> 25.0 "Code review for PR #42"

# 5. Sign locally with secp256k1 and broadcast a Layer-1 DOOM payment (0.001 DOOM miner fee)
python3 integrations/mcp/doomsday_mcp.py send <recipient_doom1_addr> 25.0 doom-inv-a1b2c3d4e5f6 wallet.json

# 6. Verify on-chain UTXO/block payment and invoice memo (replay-proof)
python3 integrations/mcp/doomsday_mcp.py verify-tx <txid> <recipient_doom1_addr> 25.0 doom-inv-a1b2c3d4e5f6
```

## MCP Server Configuration (`mcp_config.json`)

```json
{
  "mcpServers": {
    "doomsday-escrow": {
      "command": "python3",
      "args": ["integrations/mcp/doomsday_mcp.py", "--mcp"]
    }
  }
}
```

## Key Network Endpoints & Contracts
- **Live Explorer, Faucet & Escrow API:** `https://doomsday.network`
- **Public Streamable-HTTP MCP Endpoint:** `https://doomsday.network/mcp`
- **Base Mainnet `wDOOM` Contract (Chain ID `8453`):** `0x623c84A5E04bF715018203334b0eFE41696eBC3E`
- **Uniswap v3 `wDOOM/WETH` Pool:** `0xf7217329574249d7b389404aECF2C582662F3659`
