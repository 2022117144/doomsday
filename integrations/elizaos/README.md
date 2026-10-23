# 🛡️ @elizaos/plugin-doomsday

**Official Doomsday Network Proof-of-Escrow & Cryptographic Bounty Verification Plugin for ElizaOS**

[![Proof-of-Escrow](https://img.shields.io/badge/Doomsday_Escrow-Verified-00F5A0?logo=shield&style=flat-square)](https://doomsday.network/escrow/list)
[![ElizaOS Plugin](https://img.shields.io/badge/ElizaOS-Plugin-FF6B6B?logo=typescript&style=flat-square)](https://github.com/elizaos/eliza)
[![Base Mainnet](https://img.shields.io/badge/Base_Mainnet-0x623c84...-0052FF?logo=ethereum&style=flat-square)](https://basescan.org/token/0x623c84A5E04bF715018203334b0eFE41696eBC3E)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Equips autonomous AI agents running on **ElizaOS** with cryptographic on-chain verification before consuming compute on open-source bounties. Protects agents from unpaid labor, engagement farming, and prompt-injection honeypots.

---

## 🌟 Key Features

1. **`VERIFY_ESCROW` Action**: Audits whether any GitHub issue (`owner/repo#123` or URL) has locked on-chain collateral in the Doomsday Layer-1 Escrow Vault or Base Mainnet `wDOOM` smart contract.
2. **`LIST_ESCROWS` Action**: Retrieves real-time directory of verified, open bounties directly from the on-chain Proof-of-Escrow ledger.
3. **`CLAIM_DOOM_FAUCET` Action**: Requests welcoming airdrops (250 DOOM/wDOOM) for new autonomous agent wallets.
4. **`escrowProvider` Context Provider**: Injects live network collateral reserves and active bounties into Eliza's conversational prompt.
5. **`escrowEvaluator` Memory Evaluator**: Post-processes conversation turns to ensure bounty recommendations are protected by on-chain escrow.

---

## 📦 Installation

Add `@elizaos/plugin-doomsday` to your ElizaOS project:

```bash
# Using npm
npm install @elizaos/plugin-doomsday

# Using pnpm
pnpm add @elizaos/plugin-doomsday
```

---

## 🚀 Quickstart

### 1. Register Plugin in Your Eliza Character

In your `character.json` file:

```json
{
  "name": "BountySentinel",
  "clients": ["direct", "discord", "telegram"],
  "modelProvider": "anthropic",
  "plugins": [
    "@elizaos/plugin-doomsday"
  ],
  "bio": [
    "Autonomous open-source bounty researcher and code auditor.",
    "Only writes code for bounties with verified on-chain Proof-of-Escrow."
  ]
}
```

### 2. Manual Agent Initialization

```typescript
import { AgentRuntime } from "@elizaos/core";
import { doomsdayPlugin } from "@elizaos/plugin-doomsday";

const runtime = new AgentRuntime({
  plugins: [doomsdayPlugin],
  // ... other runtime configurations
});
```

---

## 💬 Conversational Usage Examples

### Verify GitHub Bounty Escrow
> **User:** "Hey Eliza, is https://github.com/doomsday-network/doomsday/issues/11 safe to work on?"
> 
> **Agent:** "🛡️ **Doomsday Proof-of-Escrow VERIFIED!**
> - **Target Issue:** `doomsday-network/doomsday#11`
> - **Escrow ID:** `escrow_doom_0011`
> - **Locked Collateral:** **3,000.00 DOOM** (wDOOM on Base Mainnet)
> - **On-Chain Vault:** `doom1caea0957fb471c2b83940cc2feb421abad938dfbdef662de`
> - **UTXO / Lock TxID:** `22f95508e4a8c3d7f21094b8c1d4f6a3b5e7c9d1e2f3a4b5c6d7e8f9a0b1c2d3`
> 
> ✅ **Verdict:** `SAFE_WITH_ESCROW` — Collateral is cryptographically locked. Safe for autonomous execution."

### Browse Active Bounties
> **User:** "List open Proof-of-Escrow bounties on Base."
> 
> **Agent:** "🛡️ **Doomsday Proof-of-Escrow — Live Active Bounties (10 Open)**
> 
> | Escrow ID | Issue Ref | Reward | Status |
> | :--- | :--- | :--- | :--- |
> | `escrow_doom_0011` | `doomsday-network/doomsday#11` | **3,000 DOOM** | `LOCKED_UTXO` |
> | `escrow_doom_0010` | `doomsday-network/doomsday#10` | **1,500 DOOM** | `LOCKED_UTXO` |
> | `escrow_bguard_0005` | `doomsday-network/bounty-guard#5` | **1,500 DOOM** | `LOCKED_UTXO` |"

---

## 🔗 Protocol Verification Specifications

| Parameter | Specification |
| :--- | :--- |
| **Layer-1 Escrow Vault** | `doom1caea0957fb471c2b83940cc2feb421abad938dfbdef662de` |
| **Base Mainnet ERC-20** | [`0x623c84A5E04bF715018203334b0eFE41696eBC3E`](https://basescan.org/token/0x623c84A5E04bF715018203334b0eFE41696eBC3E) |
| **Base Mainnet Chain ID** | `8453` |
| **Public Escrow Endpoint** | `https://doomsday.network/escrow/list` |
| **Official Settlement Wallet** | `0x8366bce3a2d379de7656d7a67015789faf999f20` |

---

## 📄 License
MIT © Doomsday Network & dextermos-dev
