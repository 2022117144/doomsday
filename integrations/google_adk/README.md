# Google ADK Proof-of-Escrow Integration

Read-only Doomsday escrow tools for [Google Agent Development Kit](https://google.github.io/adk-docs/) agents. Google ADK is optional; the HTTP client is standard-library only.

## Quickstart

```bash
python -m pip install google-adk
python -m unittest tests.test_google_adk_integration -v
```

```python
from google.adk.agents import LlmAgent
from integrations.google_adk.doomsday_tool import google_adk_tools

bounty_agent = LlmAgent(
    name="bounty_agent",
    model="gemini-2.5-flash",
    instruction="Verify Proof-of-Escrow before spending compute on a bounty.",
    tools=google_adk_tools(),
)
```

## Tools

| Function | Purpose |
| :--- | :--- |
| `verify_doomsday_escrow(owner, repo, issue_number)` | Read one issue's escrow status and locked amount |
| `list_doomsday_escrows()` | List open escrows and aggregate totals |
| `get_doomsday_worker_status(doom1_address)` | Inspect a miner worker's telemetry and shares |

ADK derives each `FunctionTool` declaration from the Python signature and Google-style docstring in `doomsday_tool.py`.

## Boundary

These tools report the first-party Doomsday API response. They do not independently re-derive L1 UTXOs or Base ERC-20 balances, and escrow presence is not proof of payment. HTTP failures return `status: ERROR` or `NETWORK_FAILURE`; invalid input returns `INVALID_INPUT`.
