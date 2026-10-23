/**
 * ElizaOS Action: CLAIM_DOOM_FAUCET
 * Claims early adopter DOOM or wDOOM tokens via the welcome faucet.
 */

import { Action, IAgentRuntime, Memory, State, HandlerCallback } from "@elizaos/core";
import { DoomsdayEscrowClient } from "../client.js";

export const claimFaucetAction: Action = {
  name: "CLAIM_DOOM_FAUCET",
  similes: [
    "GET_FREE_DOOM",
    "CLAIM_WELCOME_AIRDROP",
    "REQUEST_TEST_DOOM",
    "CLAIM_WDOOM_FAUCET"
  ],
  description:
    "Requests early adopter welcoming tokens (250 DOOM or wDOOM on Base Mainnet) from the Doomsday test/faucet relayer.",

  validate: async (_runtime: IAgentRuntime, message: Memory, _state?: State): Promise<boolean> => {
    const text = message.content?.text || "";
    return /claim|faucet|airdrop|free/i.test(text) && /doom|wdoom/i.test(text);
  },

  handler: async (
    _runtime: IAgentRuntime,
    message: Memory,
    _state?: State,
    _options?: any,
    callback?: HandlerCallback
  ): Promise<boolean> => {
    const text = message.content?.text || "";

    // Extract wallet address (0x... for Base or doom1... for L1)
    const baseMatch = text.match(/0x[a-fA-F0-9]{40}/);
    const doomMatch = text.match(/doom1[a-zA-Z0-9]{38,60}/);
    const targetAddress = baseMatch ? baseMatch[0] : doomMatch ? doomMatch[0] : "";

    if (!targetAddress) {
      if (callback) {
        callback({
          text: "⚠️ Please provide your recipient wallet address (e.g. `0x...` on Base Mainnet or `doom1...` on Doomsday L1) to claim the welcome faucet.",
          content: { error: "MISSING_WALLET_ADDRESS" }
        });
      }
      return false;
    }

    const client = new DoomsdayEscrowClient();
    const result = await client.claimFaucet(targetAddress);

    let responseText = "";
    if (result.success) {
      responseText = `🎉 **Doomsday Welcome Faucet Claim Successful!**\n\n` +
        `- **Recipient:** \`${result.recipient}\`\n` +
        `- **Network:** ${result.payout_network}\n` +
        `- **Disbursed Amount:** **${result.amount_doom} DOOM / wDOOM**\n` +
        (result.txid ? `- **Transaction ID:** \`${result.txid}\`\n` : "") +
        `\nTokens are on their way to your self-custody wallet!`;
    } else {
      responseText = `⚠️ **Faucet Claim Notice:** ${result.message}`;
    }

    if (callback) {
      callback({
        text: responseText,
        content: result
      });
    }

    return result.success;
  },

  examples: [
    [
      {
        user: "{{user1}}",
        content: { text: "Can you claim the 250 DOOM welcome airdrop for my wallet 0x8366bCe3a2D379Dec7656D7A67015789FaF999f20?" }
      },
      {
        user: "{{agentName}}",
        content: {
          text: "🎉 **Doomsday Welcome Faucet Claim Successful!**\n\n- **Recipient:** `0x8366bCe3a2D379Dec7656D7A67015789FaF999f20`\n- **Network:** Base Mainnet\n- **Disbursed Amount:** **250 DOOM / wDOOM**",
          action: "CLAIM_DOOM_FAUCET"
        }
      }
    ]
  ]
};
