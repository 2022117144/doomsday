#!/usr/bin/env node
/**
 * Doomsday Network <-> Base Mainnet Proof-of-Reserve Bridge Relayer
 * 
 * Continuously monitors native Doomsday blockchain blocks for deposits sent to the
 * 1:1 reserve vault (doom1vault000000000000000000000000000000).
 * When a valid deposit is confirmed with an EVM destination address in extra_data,
 * this daemon submits an on-chain transaction to WrappedDOOM (wDOOM) on Base to mint
 * the corresponding 1:1 wDOOM tokens directly to the user's EVM wallet.
 */

const fs = require('fs');
const path = require('path');
const { ethers } = require('ethers');

const ENV_FILE = path.resolve(__dirname, '.env.base');
const STATE_FILE = path.resolve(__dirname, 'build', 'bridge_state.json');
const WDOOM_ARTIFACT = path.resolve(__dirname, 'build', 'WrappedDOOM.json');

const VAULT_ADDRESS = 'doom1vault000000000000000000000000000000';
const DEFAULT_NODE_URL = 'https://doomsday.network';
const DEFAULT_BASE_RPC = 'https://mainnet.base.org';
const DEFAULT_WDOOM_ADDRESS = '0x623c84A5E04bF715018203334b0eFE41696eBC3E';
const POLL_INTERVAL_MS = 10000; // 10 seconds

function loadEnv() {
  if (fs.existsSync(ENV_FILE)) {
    const content = fs.readFileSync(ENV_FILE, 'utf8');
    content.split('\n').forEach(line => {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
        const [k, ...v] = trimmed.split('=');
        if (!process.env[k.trim()]) {
          process.env[k.trim()] = v.join('=').trim();
        }
      }
    });
  }
}

function loadState() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    }
  } catch (e) {}
  return { lastScannedHeight: 0, processedTxs: [] };
}

function saveState(state) {
  try {
    const dir = path.dirname(STATE_FILE);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf8');
  } catch (e) {
    console.error('[Bridge] Failed to save state:', e.message);
  }
}

async function fetchJson(url) {
  const res = await fetch(url, { headers: { 'User-Agent': 'DoomsdayBridgeRelayer/1.0' } });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return await res.json();
}

async function main() {
  loadEnv();

  const nodeUrl = (process.env.DOOMSDAY_RPC_URL || DEFAULT_NODE_URL).replace(/\/$/, '');
  const baseRpc = process.env.BASE_MAINNET_RPC || DEFAULT_BASE_RPC;
  const wDoomAddress = process.env.WDOOM_CONTRACT_ADDRESS || DEFAULT_WDOOM_ADDRESS;
  const privateKey = process.env.EVM_PRIVATE_KEY;

  if (!privateKey) {
    console.error('❌ EVM_PRIVATE_KEY is missing in .env.base. Relayer cannot sign mint transactions.');
    process.exit(1);
  }

  console.log('=============================================================');
  console.log('🌉 DOOMSDAY NETWORK <-> BASE MAINNET BRIDGE RELAYER');
  console.log('=============================================================');
  console.log(`Doomsday Node:    ${nodeUrl}`);
  console.log(`Reserve Vault:    ${VAULT_ADDRESS}`);
  console.log(`Base RPC:         ${baseRpc}`);
  console.log(`wDOOM Contract:   ${wDoomAddress}`);
  console.log('=============================================================\n');

  const provider = new ethers.JsonRpcProvider(baseRpc);
  const wallet = new ethers.Wallet(privateKey, provider);
  console.log(`Relayer Address:  ${wallet.address}`);

  const { abi } = JSON.parse(fs.readFileSync(WDOOM_ARTIFACT, 'utf8'));
  const contract = new ethers.Contract(wDoomAddress, abi, wallet);

  // Check relayer authorization
  const isRelayer = await contract.isBridgeRelayer(wallet.address);
  const isOwner = (await contract.owner()).toLowerCase() === wallet.address.toLowerCase();
  if (!isRelayer && !isOwner) {
    console.error(`❌ Wallet ${wallet.address} is NOT an authorized bridge relayer on contract ${wDoomAddress}!`);
    process.exit(1);
  }
  console.log(`✓ Relayer Authorization: Confirmed (Owner: ${isOwner}, Relayer: ${isRelayer})`);

  let state = loadState();

  if (state.lastScannedHeight === 0) {
    try {
      const status = await fetchJson(`${nodeUrl}/status`);
      state.lastScannedHeight = Math.max(0, status.height - 20);
      saveState(state);
      console.log(`Initial scan starting from block height: #${state.lastScannedHeight}`);
    } catch (e) {
      console.warn(`Could not fetch tip height, starting from 0: ${e.message}`);
    }
  } else {
    console.log(`Resuming scan from block height: #${state.lastScannedHeight}`);
  }

  const runLoop = async () => {
    try {
      const status = await fetchJson(`${nodeUrl}/status`);
      const tip = status.height;
      // Require 2 confirmations (tip - 1) before minting on Base to protect against 1-block orphans
      const safeTip = Math.max(0, tip - 1);

      if (safeTip > state.lastScannedHeight) {
        const fromH = state.lastScannedHeight + 1;
        const limit = Math.min(50, safeTip - fromH + 1);

        // Fetch exact sequential range from P2P block synchronization endpoint
        const blocks = await fetchJson(`${nodeUrl}/p2p/blocks?start_height=${fromH}&limit=${limit}`);
        const ordered = [...blocks].sort((a, b) => a.height - b.height);

        for (const block of ordered) {
          if (block.height <= state.lastScannedHeight) continue;
          if (block.height > safeTip) break;

          for (const tx of (block.transactions || [])) {
            // Check outputs for vault deposit
            for (const out of (tx.outputs || [])) {
              if (out.recipient === VAULT_ADDRESS) {
                const amountDoom = out.amount / 100000000;
                const extraData = (tx.extra_data || '').trim();

                console.log(`\n🔍 [Block #${block.height}] Vault deposit detected in tx ${tx.txid.slice(0, 16)}...`);
                console.log(`   Amount: ${amountDoom} DOOM | Memo/ExtraData: "${extraData}"`);

                if (!extraData.startsWith('0x') || extraData.length !== 42) {
                  console.warn(`   ⚠️ Invalid or missing EVM recipient address in extra_data. Cannot mint wDOOM.`);
                  continue;
                }

                const evmRecipient = ethers.getAddress(extraData);
                const alreadyProcessed = await contract.processedDoomsdayTxs(tx.txid);

                if (alreadyProcessed) {
                  console.log(`   ℹ️ Transaction ${tx.txid.slice(0, 16)}... was already processed on-chain.`);
                  continue;
                }

                // 1 DOOM = 10^8 Sparks. wDOOM = 18 decimals (10^18 units).
                // amountWei = BigInt(out.amount) * 10^10
                const amountWei = BigInt(out.amount) * 10000000000n;

                console.log(`   🚀 Minting ${amountDoom} wDOOM on Base to ${evmRecipient}...`);
                const mintTx = await contract.mintFromNative(evmRecipient, amountWei, tx.txid);
                console.log(`   Submitted mint tx: ${mintTx.hash}`);
                await mintTx.wait();
                console.log(`   🎉 wDOOM Mint Confirmed on Base! (Tx: ${mintTx.hash})`);
              }
            }
          }

          state.lastScannedHeight = block.height;
          saveState(state);
        }
      }
    } catch (err) {
      console.error(`[Bridge Error] ${err.message}`);
    }

    setTimeout(runLoop, POLL_INTERVAL_MS);
  };

  runLoop();
}

main().catch(err => {
  console.error('Fatal Bridge Relayer Error:', err);
  process.exit(1);
});
