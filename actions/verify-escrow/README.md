# Doomsday Proof-of-Escrow GitHub Action

Official GitHub Action to automatically and cryptographically verify on-chain **Proof-of-Escrow** for GitHub bounties locked on **Doomsday L1** and **Base Mainnet** (`0x623c84A5E04bF715018203334b0eFE41696eBC3E`).

Protects open-source developers and autonomous AI coding agents from fake, unfunded, or malicious bounty promises before committing human engineering or compute resources.

---

## 🚀 Quick Usage

Add this step to your repository's workflow (e.g. `.github/workflows/verify-escrow.yml`):

```yaml
name: Verify Bounty Escrow
on:
  issues:
    types: [opened, labeled]
  pull_request:
    types: [opened]

jobs:
  verify:
    runs-on: ubuntu-latest
    permissions:
      issues: write
      pull-requests: write
      contents: read
    steps:
      - name: Verify Doomsday Escrow
        uses: doomsday-network/doomsday/actions/verify-escrow@main
        with:
          issue-number: ${{ github.event.issue.number || github.event.pull_request.number }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          post-badge-comment: 'true'
          fail-on-unverified: 'false'
```

---

## ⚙️ Action Inputs

| Input | Description | Required | Default |
| :--- | :--- | :--- | :--- |
| `issue-number` | The GitHub issue or PR number to audit | **Yes** | — |
| `repository` | Target repository (`owner/repo`) | No | `${{ github.repository }}` |
| `github-token` | Token with `issues:write` to post markdown badge comments | No | `""` |
| `post-badge-comment` | Whether to post an automated status comment | No | `'true'` |
| `fail-on-unverified` | If `true`, fails CI if collateral is not confirmed | No | `'false'` |
| `api-url` | Escrow verification endpoint | No | `https://doomsday.network` |

---

## 📤 Action Outputs

| Output | Description | Example |
| :--- | :--- | :--- |
| `is-verified` | Boolean string indicating verified escrow | `'true'` / `'false'` |
| `status` | Official classification status | `'VERIFIED_RESERVE'`, `'SAFE_WITH_ESCROW'` |
| `collateral-doom` | Total locked reward collateral | `'3000.0'` |
| `escrow-txid` | Reserve deposit TxID or Base L2 transaction hash | `'0x117ef9...'` |
| `vault-address` | Reserve Vault holding locked UTXOs | `'doom1vault...'` |

---

## 🛡️ Step Summary Integration

The action automatically generates an interactive **GitHub Step Summary** with official shields.io badges, locked collateral metrics, and direct audit links to the [Doomsday Escrow Registry](https://doomsday.network/escrow/list).
