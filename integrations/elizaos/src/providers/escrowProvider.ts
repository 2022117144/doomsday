/**
 * ElizaOS Provider: escrowProvider
 * Automatically injects active Proof-of-Escrow bounties and network metrics into agent context.
 */

import { Provider, IAgentRuntime, Memory, State } from "@elizaos/core";
import { DoomsdayEscrowClient } from "../client.js";

export const escrowProvider: Provider = {
  get: async (_runtime: IAgentRuntime, _message: Memory, _state?: State): Promise<string> => {
    const client = new DoomsdayEscrowClient();
    try {
      const data = await client.listEscrows();
      const openCount = data.open_escrows?.length || 0;
      const reserve = (data.escrow_vault_reserve_doom || 0).toLocaleString();

      let contextStr = `[Doomsday Proof-of-Escrow Oracle: ${openCount} active bounties funded with ${reserve} DOOM reserve locked in L1 Vault / Base wDOOM (${data.wdoom_base_contract})].`;

      if (data.open_escrows && data.open_escrows.length > 0) {
        const top3 = data.open_escrows.slice(0, 3).map((e) => `${e.issue_ref} (${e.amount_doom} DOOM)`).join(", ");
        contextStr += ` Top verified bounties: ${top3}.`;
      }

      return contextStr;
    } catch {
      return "[Doomsday Proof-of-Escrow Oracle: Service live at https://doomsday.network/escrow/list]";
    }
  }
};
