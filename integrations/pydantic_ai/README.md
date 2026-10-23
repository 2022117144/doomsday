# Pydantic AI Proof-of-Escrow Integration

Typed, read-only Doomsday escrow tools for [Pydantic AI](https://ai.pydantic.dev/) agents. Pydantic AI is optional; the HTTP client uses only the Python standard library.

## Quickstart

```bash
python -m pip install pydantic-ai
python -m unittest tests.test_pydantic_ai_integration -v
```

```python
from pydantic_ai import Agent
from integrations.pydantic_ai.doomsday_tool import pydantic_ai_tools

bounty_agent = Agent(
    "google-gla:gemini-2.5-flash",
    instructions="Verify Proof-of-Escrow before spending compute on a bounty.",
    tools=pydantic_ai_tools(),
)
result = bounty_agent.run_sync(
    "Verify doomsday-network/bounty-guard#5 before doing any work."
)
print(result.output)
```

You can also decorate the plain functions directly:

```python
from pydantic_ai import Agent
from integrations.pydantic_ai.doomsday_tool import verify_doomsday_escrow, list_doomsday_escrows

agent = Agent("google-gla:gemini-2.5-flash")
agent.tool_plain(verify_doomsday_escrow)
agent.tool_plain(list_doomsday_escrows)
```

## Tools

| Function | Purpose |
| :--- | :--- |
| `verify_doomsday_escrow(owner, repo, issue_number)` | Read one issue's escrow status and locked amount |
| `list_doomsday_escrows()` | List open escrows and aggregate totals |
| `get_doomsday_worker_status(doom1_address)` | Inspect a miner worker's telemetry and shares |

## Boundary

These tools report the first-party Doomsday API response. They do not independently re-derive L1 UTXOs or Base ERC-20 balances, and escrow presence is not proof that a bounty was paid. HTTP failures return `status: ERROR` or `NETWORK_FAILURE`; input failures return `INVALID_INPUT`, never a false verified result.
