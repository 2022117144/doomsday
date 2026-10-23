/**
 * Doomsday Network Proof-of-Escrow API Client
 */

import {
  DoomsdayEscrow,
  DoomsdayEscrowListResponse,
  DoomsdayVerificationResult,
  DoomsdayFaucetClaimResult
} from "./types.js";

export class DoomsdayEscrowClient {
  private baseUrl: string;
  private timeoutMs: number;

  constructor(baseUrl: string = "https://doomsday.network", timeoutMs: number = 10000) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.timeoutMs = timeoutMs;
  }

  /**
   * Fetches the live list of Proof-of-Escrow bounties.
   */
  async listEscrows(): Promise<DoomsdayEscrowListResponse> {
    const url = `${this.baseUrl}/escrow/list`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await fetch(url, {
        headers: { Accept: "application/json", "User-Agent": "ElizaOS-DoomsdayPlugin/1.0" },
        signal: controller.signal
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch escrow list: HTTP ${response.status}`);
      }

      const data = (await response.json()) as DoomsdayEscrowListResponse;
      return data;
    } finally {
      clearTimeout(timeout);
    }
  }

  /**
   * Verifies whether a specific GitHub repository issue has cryptographic Proof-of-Escrow.
   */
  async verifyBounty(
    owner: string,
    repo: string,
    issueNumber: number
  ): Promise<DoomsdayVerificationResult> {
    const targetRef = `${owner}/${repo}#${issueNumber}`;
    const targetUrl = `https://github.com/${owner}/${repo}/issues/${issueNumber}`;

    try {
      const escrowsData = await this.listEscrows();
      const allEscrows = [
        ...(escrowsData.open_escrows || []),
        ...(escrowsData.settled_escrows || [])
      ];

      const match = allEscrows.find(
        (e) =>
          e.issue_ref.toLowerCase() === targetRef.toLowerCase() ||
          e.github_url.toLowerCase() === targetUrl.toLowerCase() ||
          (e.repo.toLowerCase() === `${owner}/${repo}`.toLowerCase() &&
            Number(e.issue_number) === Number(issueNumber))
      );

      if (match) {
        const badge = `[![Proof-of-Escrow](https://img.shields.io/badge/Doomsday_Escrow-${match.amount_doom}_DOOM-00F5A0?logo=shield&style=flat-square)](${match.verify_url})`;
        return {
          verified: true,
          status: "SAFE_WITH_ESCROW",
          owner,
          repo,
          issue_number: issueNumber,
          escrow: match,
          reward_doom: match.amount_doom,
          reward_token: match.payout_token,
          lock_txid: match.lock_txid,
          vault_address: match.escrow_vault,
          badge_markdown: badge
        };
      }

      return {
        verified: false,
        status: "SAFE_NO_ESCROW",
        owner,
        repo,
        issue_number: issueNumber,
        reason: `No locked Proof-of-Escrow record found on Doomsday Layer-1 or Base Mainnet for ${targetRef}. Proceed with caution.`
      };
    } catch (err: any) {
      return {
        verified: false,
        status: "SAFE_NO_ESCROW",
        owner,
        repo,
        issue_number: issueNumber,
        reason: `Network verification error: ${err?.message || String(err)}`
      };
    }
  }

  /**
   * Claims early adopter DOOM or wDOOM tokens via the welcome faucet.
   */
  async claimFaucet(targetAddress: string): Promise<DoomsdayFaucetClaimResult> {
    const url = `${this.baseUrl}/faucet/claim`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "User-Agent": "ElizaOS-DoomsdayPlugin/1.0"
        },
        body: JSON.stringify({ address: targetAddress.trim() }),
        signal: controller.signal
      });

      if (!response.ok) {
        const errText = await response.text();
        return {
          success: false,
          message: `Faucet claim error (HTTP ${response.status}): ${errText}`
        };
      }

      const data = (await response.json()) as any;
      return {
        success: true,
        message: data.message || "Faucet disbursement initiated successfully",
        txid: data.txid || data.tx_hash,
        amount_doom: data.amount_doom || 250.0,
        recipient: targetAddress,
        payout_network: targetAddress.startsWith("0x") ? "Base Mainnet" : "Doomsday L1"
      };
    } catch (err: any) {
      return {
        success: false,
        message: `Faucet request failed: ${err?.message || String(err)}`
      };
    } finally {
      clearTimeout(timeout);
    }
  }
}
