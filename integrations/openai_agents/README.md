# OpenAI Agents SDK Proof-of-Escrow Integration

A dependency-light Doomsday Proof-of-Escrow tool for [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) workflows.

Agents can check whether a GitHub bounty has verified on-chain escrow before spending tokens, writing code, or opening a pull request.

## Quickstart

Install the optional SDK:

```bash
python -m pip install openai-agents
```

Register the function tool on an agent:

```python
from agents import Agent
from integrations.openai_agents.doomsday_tool import verify_doomsday_escrow

bounty_agent = Agent(
    name="Bounty agent",
    instructions="Check Proof-of-Escrow before working on a funded issue.",
    tools=[verify_doomsday_escrow],
)
```

The tool accepts:

| Argument | Meaning |
| :--- | :--- |
| `owner` | GitHub repository owner, e.g. `doomsday-network` |
| `repo` | GitHub repository name, e.g. `doomsday` |
| `issue` | Positive GitHub issue number, e.g. `11` |

It returns the Doomsday API response as JSON, including the current escrow status, locked DOOM amount, and evidence level.

## Zero-dependency client

The HTTP client uses only the Python standard library, so it also works without the OpenAI Agents SDK:

```python
from integrations.openai_agents.doomsday_tool import DoomsdayEscrowClient

client = DoomsdayEscrowClient()
result = client.verify("doomsday-network", "doomsday", 11)
print(result["status"], result.get("locked_doom"))
```

## Test

From the repository root:

```bash
python -m unittest tests.test_openai_agents_integration -v
```

## Boundary

The integration reports Doomsday's API response. It does not independently re-derive the L1 UTXO or Base ERC-20 state, and an escrow response is not proof that a bounty has been paid. Network failures remain `status: ERROR`/`NETWORK_FAILURE`; they are never promoted to a verified escrow.
