# Haystack Proof-of-Escrow Integration

Read-only Doomsday escrow tools for [Haystack](https://haystack.deepset.ai/) agents and pipelines. Haystack is optional; the HTTP client uses only Python's standard library.

## Quickstart

```bash
python -m pip install haystack-ai
python -m unittest tests.test_haystack_integration -v
```

```python
from haystack.components.agents import Agent
from integrations.haystack.doomsday_tool import haystack_tools

agent = Agent(chat_generator=your_chat_generator, tools=haystack_tools())
result = agent.run(
    "Verify doomsday-network/bounty-guard#5 before doing any bounty work."
)
print(result)
```

## Tools

| Tool | Purpose |
| :--- | :--- |
| `verify_doomsday_escrow(owner, repo, issue_number)` | Read one issue's escrow status and locked amount |
| `list_doomsday_escrows()` | List open escrows and aggregate totals |
| `get_doomsday_worker_status(doom1_address)` | Inspect a miner worker's telemetry and shares |

Each tool generates its JSON schema from typed parameters and docstrings.

## Boundary

The tools report the first-party Doomsday API response. They do not independently re-derive L1 UTXOs or Base ERC-20 balances, and escrow presence is not proof of payment. HTTP failures return `status: ERROR` or `NETWORK_FAILURE`; invalid input returns `INVALID_INPUT`.
