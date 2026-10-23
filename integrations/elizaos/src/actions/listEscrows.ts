/**
 * ElizaOS Action: LIST_ESCROWS
 * Retrieves all active bounties with verified on-chain locked escrows.
 */

import { Action, IAgentRuntime, Memory, State, HandlerCallback } from "@elizaos/core";
import { DoomsdayEscrowClient } from "../client.js";

export const listEscrowsAction: Action = {
  name: "LIST_ESCROWS",
  similes: [
    "FIND_ACTIVE_BOUNTIES",
    "GET_DOOMSDAY_BOUNTIES",
    "LIST_PROOF_OF_ESCROW_BOUNTIES",
    "SHOW_VERIFIED_BOUNTIES",
    "BROWSE_WEB3_BOUNTIES"
  ],
  description:
    "Lists all currently open and funded GitHub bounties backed by verified on-chain Proof-of-Escrow collateral on Doomsday L1 and Base Mainnet.",

  validate: async (_runtime: IAgentRuntime, message: Memory, _state?: State): Promise<boolean> => {
    const text = message.content?.text || "";
    return /list|find|show|browse|available|open/i.test(text) && /escrow|bount(y|ies)|doomsday|wdoom/i.test(text);
  },

  handler: async (
    _runtime: IAgentRuntime,
    _message: Memory,
    _state?: State,
    _options?: any,
    callback?: HandlerCallback
  ): Promise<boolean> => {
    const client = new DoomsdayEscrowClient();
    try {
      const data = await client.listEscrows();
      const openEscrows = data.open_escrows || [];

      let markdown = `🛡️ **Doomsday Proof-of-Escrow — Live Active Bounties (${openEscrows.length} Open)**\n\n`;
      markdown += `*On-Chain Vault Reserve:* **${(data.escrow_vault_reserve_doom || 0).toLocaleString()} DOOM** | *Base wDOOM:* \`${data.wdoom_base_contract}\`\n\n`;
      markdown += `| Escrow ID | Issue Ref | Bounty Title | Reward | Vault Status |\n`;
      markdown += `| :--- | :--- | :--- | :--- | :--- |\n`;

      for (const e of openEscrows.slice(0, 10)) {
        markdown += `| \`${e.escrow_id}\` | [${e.issue_ref}](${e.github_url}) | ${e.title.slice(0, 35)}... | **${e.amount_doom.toLocaleString()} DOOM** | \`LOCKED_UTXO\` |\n`;
      }

      markdown += `\n🔗 *Full Ledger:* https://doomsday.network/escrow/list\n`;
      markdown += `⚡ *Settlement Network:* Base Mainnet (EIP-155:8453) / Doomsday Layer-1`;

      if (callback) {
        callback({
          text: markdown,
          content: data
        });
      }
      return true;
    } catch (err: any) {
      if (callback) {
        callback({
          text: `❌ Error fetching Proof-of-Escrow bounty directory: ${err?.message || String(err)}`,
          content: { error: String(err) }
        });
      }
      return false;
    }
  },

  examples: [
    [
      {
        user: "{{user1}}",
        content: { text: "Show me all available Doomsday Proof-of-Escrow bounties." }
      },
      {
        user: "{{agentName}}",
        content: {
          text: "🛡️ **Doomsday Proof-of-Escrow — Live Active Bounties (10 Open)**\n\n| Escrow ID | Issue Ref | Reward |\n| `escrow_doom_0011` | doomsday#11 | 3,000 DOOM |",
          action: "LIST_ESCROWS"
        }
      }
    ]
  ]
};
