# Doomsday Proof-of-Escrow for LlamaIndex

Seamlessly equip your **LlamaIndex** agents and agentic workflows with cryptographic proof-of-escrow verification before executing software development tasks on GitHub bounties.

## Features

- **Autonomous Verification:** Allows LlamaIndex agents to query `/escrow/{owner}/{repo}/{issue_number}`.
- **Collateral Auditing:** Inspect locked DOOM collateral, Base L2 token transfers, and reserve vault status.
- **Zero-Dependency Fallback:** Works natively with standard Python `urllib` if LlamaIndex is running in lightweight microservice environments.

## Quickstart

```python
from integrations.llamaindex.doomsday_tool import get_doomsday_llamaindex_tools
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI

# Initialize tools
tools = get_doomsday_llamaindex_tools()

# Attach to your LlamaIndex ReAct agent
llm = OpenAI(model="gpt-4o")
agent = ReActAgent.from_tools(tools, llm=llm, verbose=True)

# Query agent
response = agent.chat("Check if issue #11 on doomsday-network/doomsday has a verified escrow.")
print(response)
```
