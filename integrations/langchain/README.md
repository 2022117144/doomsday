# Doomsday Proof-of-Escrow — LangChain & Autonomous Agent Tools

Enables autonomous AI coding agents to verify cryptographic Proof-of-Escrow backing before allocating LLM compute or executing code generation for GitHub bounties.

### 🚀 Zero-Dependency Direct Usage

```python
from integrations.langchain.doomsday_tool import DoomsdayEscrowClient

client = DoomsdayEscrowClient()

# 1. Verify specific bounty
result = client.verify_bounty("doomsday-network", "doomsday", 11)
if result.get("locked_amount", 0) > 0:
    print(f"Verified {result['locked_amount']} DOOM locked in vault {result['vault_address']}")

# 2. List all on-chain escrows
all_escrows = client.list_escrows()
```

### 🦜 LangChain Agent Tool Integration

```python
from integrations.langchain.doomsday_tool import DoomsdayBountyVerifierTool

tools = [DoomsdayBountyVerifierTool()]
# Attach to any LangGraph, LangChain, or ReAct agent executor
```
