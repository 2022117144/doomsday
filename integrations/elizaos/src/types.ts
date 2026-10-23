/**
 * Doomsday Proof-of-Escrow Plugin Types for ElizaOS
 */

export interface DoomsdayEscrow {
  escrow_id: string;
  issue_ref: string;
  repo: string;
  issue_number: number;
  title: string;
  amount_doom: number;
  payout_token: string;
  lock_txid: string;
  escrow_vault: string;
  creator_github: string;
  release_mode: string;
  status: "OPEN" | "SETTLED" | "DISPUTED";
  created_at: number;
  github_url: string;
  verify_url: string;
}

export interface DoomsdayEscrowListResponse {
  protocol: string;
  escrow_vault_address: string;
  escrow_vault_reserve_doom: number;
  vault_utxo_verified: boolean;
  wdoom_base_contract: string;
  uniswap_v3_pool?: string;
  total_open_bounties: number;
  total_locked_doom: number;
  total_settled_bounties: number;
  total_settled_doom: number;
  open_escrows: DoomsdayEscrow[];
  settled_escrows?: DoomsdayEscrow[];
}

export interface DoomsdayVerificationResult {
  verified: boolean;
  status: "SAFE_WITH_ESCROW" | "SAFE_NO_ESCROW" | "QUARANTINE" | "NOT_FOUND";
  owner: string;
  repo: string;
  issue_number: number;
  escrow?: DoomsdayEscrow;
  reward_doom?: number;
  reward_token?: string;
  lock_txid?: string;
  vault_address?: string;
  reason?: string;
  badge_markdown?: string;
}

export interface DoomsdayFaucetClaimResult {
  success: boolean;
  message: string;
  txid?: string;
  amount_doom?: number;
  recipient?: string;
  payout_network?: string;
}
