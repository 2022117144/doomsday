/**
 * @elizaos/plugin-doomsday
 * Official Doomsday Network Proof-of-Escrow & Cryptographic Bounty Verification Plugin for ElizaOS
 */

import { Plugin } from "@elizaos/core";
import { verifyEscrowAction } from "./actions/verifyEscrow.js";
import { listEscrowsAction } from "./actions/listEscrows.js";
import { claimFaucetAction } from "./actions/claimFaucet.js";
import { escrowProvider } from "./providers/escrowProvider.js";
import { escrowEvaluator } from "./evaluators/escrowEvaluator.js";

export * from "./types.js";
export * from "./client.js";
export * from "./actions/verifyEscrow.js";
export * from "./actions/listEscrows.js";
export * from "./actions/claimFaucet.js";
export * from "./providers/escrowProvider.js";
export * from "./evaluators/escrowEvaluator.js";

export const doomsdayPlugin: Plugin = {
  name: "doomsday",
  description:
    "Official Doomsday Network Proof-of-Escrow plugin for ElizaOS. Enables autonomous coding agents to audit on-chain cryptographic bounty collateral, query open bounties, and prevent unpaid work.",
  actions: [verifyEscrowAction, listEscrowsAction, claimFaucetAction],
  providers: [escrowProvider],
  evaluators: [escrowEvaluator],
  services: []
};

export default doomsdayPlugin;
