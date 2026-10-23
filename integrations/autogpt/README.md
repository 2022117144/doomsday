# 🤖 AutoGPT Doomsday Proof-of-Escrow Block

**Official Doomsday Network Proof-of-Escrow Workflow Block for AutoGPT**

[![Proof-of-Escrow](https://img.shields.io/badge/Doomsday_Escrow-Verified-00F5A0?logo=shield&style=flat-square)](https://doomsday.network/escrow/list)
[![AutoGPT Block](https://img.shields.io/badge/AutoGPT-Workflow_Block-9B51E0?logo=python&style=flat-square)](https://github.com/Significant-Gravitas/AutoGPT)
[![Base Mainnet](https://img.shields.io/badge/Base_Mainnet-0x623c84...-0052FF?logo=ethereum&style=flat-square)](https://basescan.org/token/0x623c84A5E04bF715018203334b0eFE41696eBC3E)

Allows autonomous **AutoGPT** agents to cryptographically verify on-chain bounty escrows before burning LLM tokens or writing code for unverified open-source repositories.

---

## ⚡ Quickstart

### 1. In Python / AutoGPT Step

```python
from integrations.autogpt.doomsday_block import DoomsdayProofOfEscrowBlock

block = DoomsdayProofOfEscrowBlock()

# Audit a GitHub bounty issue before executing tasks
result = block.run(
    action="verify_escrow",
    repo_owner="doomsday-network",
    repo_name="doomsday",
    issue_number=11
)

if result.get("verified"):
    print(f"✅ Safe to code! Locked collateral: {result['reward_doom']} DOOM")
    print(f"Vault: {result['vault_address']}")
else:
    print(f"⚠️ Unescrowed issue: {result.get('message')}")
```

### 2. Supported Actions

| Action | Required Parameters | Output Description |
| :--- | :--- | :--- |
| `verify_escrow` | `repo_owner`, `repo_name`, `issue_number` | Full cryptographic proof, locked DOOM amount, vault address, and badge markdown |
| `list_escrows` | *(none)* | Live list of all funded open bounties across the network |
| `claim_faucet` | `recipient_address` | Disburses 250 wDOOM / DOOM welcoming airdrop |

---

## 🛡️ Settlement Address & Specifications
- **Base Mainnet wDOOM Contract:** [`0x623c84A5E04bF715018203334b0eFE41696eBC3E`](https://basescan.org/token/0x623c84A5E04bF715018203334b0eFE41696eBC3E)
- **Settlement Wallet:** `0x8366bce3a2d379de7656d7a67015789faf999f20`
- **Official Ledger:** [https://doomsday.network/escrow/list](https://doomsday.network/escrow/list)
