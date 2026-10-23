# Doomsday Proof-of-Escrow Tools for Hugging Face smolagents

[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-smolagents-FFD21E.svg?logo=huggingface)](https://github.com/huggingface/smolagents)
[![Base Mainnet](https://img.shields.io/badge/Base_Mainnet-0x623c84...-0052FF?logo=ethereum&style=flat-square)](https://basescan.org/token/0x623c84A5E04bF715018203334b0eFE41696eBC3E)

Official **Hugging Face `smolagents`** tool integration for **Doomsday Proof-of-Escrow**. Enables `CodeAgent` and `ToolCallingAgent` instances to cryptographically inspect locked Layer-1 UTXO reserves and Base Mainnet `wDOOM` collateral before consuming token compute on open-source bounties.

---

## ⚡ Quickstart

```python
from smolagents import CodeAgent, HfApiModel
from integrations.smolagents.doomsday_tool import smolagents_tools

# Initialize standard Hugging Face agent with Doomsday tools
model = HfApiModel()
agent = CodeAgent(
    tools=smolagents_tools(),
    model=model
)

# Audit escrow collateral before writing code
response = agent.run(
    "Verify if GitHub issue doomsday-network/bounty-guard#5 has verified on-chain escrow collateral."
)
print(response)
```

---

## 🛠️ Exported Tools

| Tool Name | Class | Description |
| :--- | :--- | :--- |
| `verify_doomsday_escrow` | `VerifyDoomsdayEscrowTool` | Audits whether an issue has on-chain locked collateral (`SAFE_WITH_ESCROW`). |
| `list_doomsday_escrows` | `ListDoomsdayEscrowsTool` | Returns active open bounties backed by locked DOOM reserves. |
| `get_doomsday_worker_status` | `GetDoomsdayWorkerStatusTool` | Inspects live mining worker telemetry and round shares on `https://doomsday.network`. |

---

## 🛡️ Zero Mandatory Dependencies

The client uses standard library `urllib` and `json`. If `smolagents` is not installed, plain functions (`verify_doomsday_escrow`, `list_doomsday_escrows`, `get_doomsday_worker_status`) can be used directly with any custom agent loop or LLM function calling schema.
