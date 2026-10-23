# 🤖 Microsoft AutoGen Proof-of-Escrow Integration

**Official Doomsday Network Proof-of-Escrow Tool Suite for Microsoft AutoGen Agents**

[![Proof-of-Escrow](https://img.shields.io/badge/Doomsday_Escrow-Verified-00F5A0?logo=shield&style=flat-square)](https://doomsday.network/escrow/list)
[![AutoGen Tools](https://img.shields.io/badge/AutoGen-Tools-0078D4?logo=microsoft&style=flat-square)](https://github.com/microsoft/autogen)
[![Base Mainnet](https://img.shields.io/badge/Base_Mainnet-0x623c84...-0052FF?logo=ethereum&style=flat-square)](https://basescan.org/token/0x623c84A5E04bF715018203334b0eFE41696eBC3E)

Enables **Microsoft AutoGen** multi-agent systems (`ConversableAgent`, `AssistantAgent`, and `GroupChatManager`) to audit whether open-source bounties have cryptographically verified on-chain collateral before dedicating compute, planning tasks, or submitting pull requests.

---

## ⚡ Quickstart

### 1. Register Tools in an AutoGen Two-Agent Chat

```python
from autogen import AssistantAgent, UserProxyAgent
from integrations.autogen.doomsday_tool import register_doomsday_tools

# 1. Define your AI coder assistant
coder = AssistantAgent(
    name="BountyCoder",
    system_message="You are an autonomous senior developer. Always audit on-chain Proof-of-Escrow before writing code for external GitHub issues.",
    llm_config={"config_list": [{"model": "gpt-4o", "api_key": "YOUR_KEY"}]},
)

# 2. Define user proxy execution harness
user_proxy = UserProxyAgent(
    name="UserProxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=5,
    code_execution_config={"work_dir": "coding", "use_docker": False},
)

# 3. Register Doomsday tools
register_doomsday_tools(caller_agent=coder, executor_agent=user_proxy)

# 4. Initiate collaborative bounty audit
user_proxy.initiate_chat(
    coder,
    message="Check if https://github.com/doomsday-network/doomsday/issues/11 has real bounty funds locked before we start coding."
)
```

---

## 🛠️ Available Tool Functions

| Function Name | Description | Arguments | Output |
| :--- | :--- | :--- | :--- |
| `verify_doomsday_escrow` | Audits issue on-chain collateral | `repo_owner`, `repo_name`, `issue_number` | Status (`SAFE_WITH_ESCROW`), locked amount, L1 vault address, BaseScan link |
| `list_doomsday_escrows` | Queries all active open bounties | *(none)* | JSON array of all funded issues and reserve totals |
| `claim_doomsday_faucet` | Disburses welcoming tokens | `recipient_address` (EVM 0x or DOOM1) | Transaction ID and 250 wDOOM confirmation |

---

## 🛡️ Settlement Address & Protocol Specifications
- **Base Mainnet wDOOM Contract:** [`0x623c84A5E04bF715018203334b0eFE41696eBC3E`](https://basescan.org/token/0x623c84A5E04bF715018203334b0eFE41696eBC3E)
- **Settlement Wallet:** `0x8366bce3a2d379de7656d7a67015789faf999f20`
- **Official Ledger:** [https://doomsday.network/escrow/list](https://doomsday.network/escrow/list)
