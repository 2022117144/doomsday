# Microsoft Semantic Kernel Proof-of-Escrow Integration

Read-only Doomsday escrow tools for [Microsoft Semantic Kernel](https://learn.microsoft.com/semantic-kernel/) agents. Semantic Kernel is optional; the HTTP client uses only Python's standard library.

## Quickstart

```bash
python -m pip install semantic-kernel
python -m unittest tests.test_semantic_kernel_integration -v
```

```python
from semantic_kernel import Kernel
from integrations.semantic_kernel.doomsday_tool import register_doomsday_plugin

kernel = Kernel()
plugin = register_doomsday_plugin(kernel)

result = await kernel.invoke(
    plugin_name="doomsday",
    function_name="verify_escrow",
    owner="doomsday-network",
    repo="bounty-guard",
    issue_number=5,
)
print(result)
```

## Functions

| Function | Purpose |
| :--- | :--- |
| `verify_escrow(owner, repo, issue_number)` | Read one issue's escrow status and locked amount |
| `list_escrows()` | List open escrows and aggregate totals |
| `worker_status(doom1_address)` | Inspect a miner worker's telemetry and shares |

## Boundary

The plugin reports the first-party Doomsday API response. It does not independently re-derive L1 UTXOs or Base ERC-20 balances, and an open escrow is not proof that a bounty was paid. HTTP failures return `status: ERROR` or `NETWORK_FAILURE`; invalid input returns `INVALID_INPUT`.
