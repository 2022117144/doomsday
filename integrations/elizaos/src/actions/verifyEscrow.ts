/**
 * ElizaOS Action: VERIFY_ESCROW
 * Validates whether a GitHub issue has cryptographic Proof-of-Escrow collateral.
 */

import { Action, IAgentRuntime, Memory, State, HandlerCallback } from "@elizaos/core";
import { DoomsdayEscrowClient } from "../client.js";

export const verifyEscrowAction: Action = {
  name: "VERIFY_ESCROW",
  similes: [
    "CHECK_BOUNTY_ESCROW",
    "AUDIT_BOUNTY_COLLATERAL",
    "VERIFY_BOUNTY_PAYMENT",
    "CHECK_PROOF_OF_ESCROW",
    "INSPECT_BOUNTY_SAFETY"
  ],
  description:
    "Verifies on-chain Proof-of-Escrow collateral locked in Doomsday L1 Vault or Base Mainnet contract before consuming compute on open-source GitHub bounties.",

  validate: async (_runtime: IAgentRuntime, message: Memory, _state?: State): Promise<boolean> => {
    const text = message.content?.text || "";
    // Trigger if text mentions GitHub issue, bounty, or escrow check
    return (
      /github\.com\/[^\s\/]+\/[^\s\/]+\/issues\/\d+/i.test(text) ||
      (/[a-zA-Z0-9_\-\.]+\/[a-zA-Z0-9_\-\.]+#\d+/.test(text) && /escrow|bounty|verify|check/i.test(text))
    );
  },

  handler: async (
    _runtime: IAgentRuntime,
    message: Memory,
    _state?: State,
    _options?: any,
    callback?: HandlerCallback
  ): Promise<boolean> => {
    const text = message.content?.text || "";

    // Parse issue reference
    let owner = "";
    let repo = "";
    let issueNumber = 0;

    const urlMatch = text.match(/github\.com\/([^\s\/]+)\/([^\s\/]+)\/issues\/(\d+)/i);
    if (urlMatch) {
      owner = urlMatch[1];
      repo = urlMatch[2];
      issueNumber = parseInt(urlMatch[3], 10);
    } else {
      const refMatch = text.match(/([a-zA-Z0-9_\-\.]+)\/([a-zA-Z0-9_\-\.]+)#(\d+)/);
      if (refMatch) {
        owner = refMatch[1];
        repo = refMatch[2];
        issueNumber = parseInt(refMatch[3], 10);
      }
    }

    if (!owner || !repo || !issueNumber) {
      if (callback) {
        callback({
          text: "⚠️ Please specify a valid GitHub issue (e.g., `doomsday-network/doomsday#11` or full issue URL) to verify its Proof-of-Escrow.",
          content: { error: "INVALID_ISSUE_TARGET" }
        });
      }
      return false;
    }

    const client = new DoomsdayEscrowClient();
    const result = await client.verifyBounty(owner, repo, issueNumber);

    let responseText = "";
    if (result.verified && result.escrow) {
      responseText = `🛡️ **Doomsday Proof-of-Escrow VERIFIED!**\n\n` +
        `- **Target Issue:** \`${owner}/${repo}#${issueNumber}\`\n` +
        `- **Escrow ID:** \`${result.escrow.escrow_id}\`\n` +
        `- **Locked Collateral:** **${result.escrow.amount_doom.toLocaleString()} DOOM** (${result.escrow.payout_token})\n` +
        `- **On-Chain Vault:** \`${result.escrow.escrow_vault}\`\n` +
        `- **UTXO / Lock TxID:** \`${result.escrow.lock_txid}\`\n` +
        `- **Verification URL:** ${result.escrow.verify_url}\n\n` +
        `✅ **Verdict:** \`SAFE_WITH_ESCROW\` — Funds are cryptographically secured on-chain. Safe for autonomous agent development.`;
    } else {
      responseText = `⚠️ **Proof-of-Escrow Audit Notice**\n\n` +
        `- **Target Issue:** \`${owner}/${repo}#${issueNumber}\`\n` +
        `- **Status:** \`SAFE_NO_ESCROW\`\n` +
        `- **Details:** ${result.reason || "No on-chain collateral locked in Doomsday L1 Vault or Base Mainnet."}\n\n` +
        `💡 Recommendation: Verify maintainer authenticity or request Proof-of-Escrow before writing extensive patches.`;
    }

    if (callback) {
      callback({
        text: responseText,
        content: result
      });
    }

    return true;
  },

  examples: [
    [
      {
        user: "{{user1}}",
        content: { text: "Can you verify if https://github.com/doomsday-network/doomsday/issues/11 has real bounty funds locked?" }
      },
      {
        user: "{{agentName}}",
        content: {
          text: "🛡️ **Doomsday Proof-of-Escrow VERIFIED!**\n\n- **Target Issue:** `doomsday-network/doomsday#11`\n- **Locked Collateral:** **3,000 DOOM** (wDOOM Base Mainnet)\n- **Verdict:** `SAFE_WITH_ESCROW`",
          action: "VERIFY_ESCROW"
        }
      }
    ],
    [
      {
        user: "{{user1}}",
        content: { text: "Audit the escrow on repo/project#42 before I start coding." }
      },
      {
        user: "{{agentName}}",
        content: {
          text: "Auditing on-chain collateral for `repo/project#42`...",
          action: "VERIFY_ESCROW"
        }
      }
    ]
  ]
};
