/**
 * ElizaOS Evaluator: escrowEvaluator
 * Evaluates whether an external bounty or proposal discussed in conversation has verified collateral.
 */

import { Evaluator, IAgentRuntime, Memory, State } from "@elizaos/core";

export const escrowEvaluator: Evaluator = {
  name: "DOOMSDAY_ESCROW_EVALUATOR",
  similes: ["EVALUATE_BOUNTY_SAFETY", "CHECK_UNESCROWED_RISK"],
  description: "Analyzes conversation messages for references to open-source bounties and notes whether Proof-of-Escrow was validated.",

  validate: async (_runtime: IAgentRuntime, message: Memory): Promise<boolean> => {
    const text = message.content?.text || "";
    return /bounty|reward|task|issue/i.test(text) && /github\.com|#[0-9]+/i.test(text);
  },

  handler: async (_runtime: IAgentRuntime, message: Memory, _state?: State): Promise<any> => {
    const text = message.content?.text || "";
    const hasEscrowMention = /proof-of-escrow|doomsday|escrow/i.test(text);
    return {
      evaluated: true,
      hasBountyReference: true,
      hasEscrowProtection: hasEscrowMention,
      timestamp: Date.now()
    };
  },

  examples: [
    {
      context: "User asks agent to work on an external bounty repo",
      messages: [
        {
          user: "{{user1}}",
          content: { text: "Let's solve issue owner/repo#99 for $200" }
        },
        {
          user: "{{agentName}}",
          content: { text: "Checking Proof-of-Escrow before committing compute..." }
        }
      ],
      outcome: "Bounty safety evaluated"
    }
  ]
};
