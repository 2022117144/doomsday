# Agno Proof-of-Escrow Integration

Read-only Doomsday escrow and worker-status tools for [Agno](https://docs.agno.com/) agents. The HTTP client and tests use only the Python standard library; install Agno only when attaching the tools to a live agent.

## Quickstart

~~~bash
python -m pip install agno openai
python -m unittest tests.test_agno_integration -v
~~~

Configure the model provider and its credentials as described in the [Agno tools guide](https://docs.agno.com/tools/creating-tools/python-functions). Then attach the functions to an agent:

~~~python
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from integrations.agno.doomsday_tool import agno_tools

bounty_agent = Agent(
    name="bounty_guard",
    model=OpenAIResponses(id="gpt-5.4-mini"),
    instructions=(
        "Check a bounty's escrow evidence before spending compute. "
        "Distinguish the first-party API response from independent on-chain proof."
    ),
    tools=agno_tools(),
    markdown=True,
)
bounty_agent.print_response("Check doomsday-network/bounty-guard#5.")
~~~

Agno accepts typed Python functions directly as tools; no custom wrapper or runtime dependency is required by this integration module.

## Tools

| Function | Purpose |
| :--- | :--- |
| verify_doomsday_escrow(owner, repo, issue_number) | Read one issue's escrow status and reported locked amount |
| list_doomsday_escrows() | List open escrows and first-party aggregate totals |
| get_doomsday_worker_status(doom1_address) | Inspect a miner worker's pool telemetry |

## Safety and evidence boundary

These tools are **read-only**. They do not call the faucet or submit transactions. They report the first-party Doomsday API response and do not independently re-derive L1 UTXOs or Base ERC-20 balances. An escrow listing is not proof that a bounty was accepted or paid. HTTP errors return an explicit error status; invalid inputs return INVALID_INPUT.