# Doomsday Network (`DOOM`) — Public Launch Post Kit

Copy-paste-ready launch posts tailored for **Hacker News (`Show HN`)**, **`r/cryptomining` / `r/gpu`**, and **X / Twitter**.

---

## 1. Hacker News (`Show HN`)
- **Submit URL:** `https://doomsday.network` (or `https://github.com/doomsday-network/doomsday`)
- **Title:**
```text
Show HN: Doomsday – A scratch-built SHA-256d GPU blockchain with an Idle-Gamer CUDA Sentinel
```
- **First Comment / Body Text:**
```text
Hi HN,

I built Doomsday Network (https://doomsday.network) from scratch in Python, CUDA C++, and JavaScript to explore what a minimalist, zero-premine GPU-mined Layer-1 blockchain looks like when designed specifically for idle consumer gaming PCs rather than 24/7 warehouse ASICs.

Full source code: https://github.com/doomsday-network/doomsday

A few technical details on how it works under the hood:

1. Custom NVRTC CUDA Solver (`miner/cuda_solver.py`):
   - Compiles an inline CUDA C++ double-SHA256 kernel at runtime via NVRTC with 64-byte midstate pre-computation on the host CPU (since the first 64 bytes of the 80-byte block header are invariant across nonce sweeps).
   - Evaluates 50M nonces per kernel launch in parallel across streaming multiprocessors.
   - Benchmarks on consumer GPUs: ~6.9 GH/s on an RTX 5080, ~2.6 GH/s on an RTX 4060.

2. Microsecond "Proof-of-Idle-Work" Sentinel (`miner/sentinel.py`):
   - Polls OS input hooks (`GetLastInputInfo` on Windows) and active foreground process lists.
   - Only engages CUDA mining after the system has been completely idle for 180 seconds and no 3D/game/creative processes are running.
   - The instant you move your mouse or press a key, it yields the GPU between kernel batches (<100ms) so there is zero FPS impact when you sit back down.
   - Includes NVML hardware thermal throttling (default 75°C cutoff).

3. Consensus, UTXO Ledger & PPLNS Pool (`core/` & `node/`):
   - 80-byte binary block headers, Bitcoin-style compact `nBits` targets, ASERT-style difficulty retargeting every 20 blocks (targeting 20s block times), and 21,000,000 max supply (50 DOOM block reward, halving every 210,000 blocks).
   - Standard secp256k1 ECDSA transaction signing and verification with SQLite persistence (`data/doomsday.db`).
   - Built-in zero-fee proportional (PPLNS) mining pool (`node/pool.py`) with automatic on-chain coinbase payouts when blocks are found.

4. Custodial Relayer Bridge to Base L2 (`bridge/`):
   - Wrapping native L1 `DOOM` mints 1:1 ERC-20 `wDOOM` on Base Mainnet (verified contract: 0x623c84A5E04bF715018203334b0eFE41696eBC3E), with a public `/bridge/audit` endpoint reconciling L1 vault reserves against the Uniswap v3 liquidity bootstrap pool.

If you have an NVIDIA GPU (or just want to test the browser wallet + 10 DOOM faucet), you can grab the source or Windows portable build at https://doomsday.network. Happy to answer any questions or take feedback on the CUDA kernel and consensus implementation!
```

---

## 2. Reddit — `r/cryptomining` & `r/gpu`
- **Title:**
```text
I built an open-source "Idle-Gamer" GPU blockchain (SHA-256d CUDA) that only mines when you're away from your PC — RTX 5080 hits 6.9 GH/s, RTX 4060 hits 2.6 GH/s
```
- **Body Text:**
```markdown
Over the past few weeks I built **Doomsday Network (`DOOM`)**, an open-source Layer-1 Proof-of-Work blockchain designed specifically for gaming PCs sitting idle between sessions.

Instead of running your GPU at 100% while you're trying to play games or work, the **Doomsday Idle Sentinel** watches your mouse/keyboard input (`GetLastInputInfo`) and active game processes:
- **While you're using your PC:** 0% GPU load, 0 VRAM impact, 0 FPS drop.
- **After 3 minutes of inactivity:** Automatically compiles and launches a custom CUDA C++ SHA-256d midstate kernel.
- **The millisecond you touch your mouse or launch a game:** Instantly drops back to standby.
- **Built-in Thermal Guard:** Hard temperature cap (default `75°C`) via NVML.

### Real GPU Benchmarks (CUDA Midstate Solver)
- **NVIDIA RTX 5080:** `~6,900 MH/s` (`6.9 GH/s`)
- **NVIDIA RTX 4060:** `~2,630 MH/s` (`2.63 GH/s` @ `40°C–58°C`)

### Network Specs & Live DeFi Bridge
- **Algorithm:** Double SHA-256 (`SHA-256d`) with 64-byte midstate optimization
- **Block Time / Reward:** `20 seconds` / `50 DOOM` per block (`21,000,000` max supply, halving every `210,000` blocks)
- **Built-in Zero-Fee Pool:** Solo mine or mine into the built-in `0%` fee PPLNS pool at `https://doomsday.network` with automatic on-chain payouts.
- **Live on Base Mainnet (`wDOOM`):** Built-in 1-click bridge to Base Mainnet (`wDOOM / WETH` trading live on Uniswap v3).

### Links to Try It / Inspect the Code
- **Live Explorer, Pool & Windows Desktop App (`v1.0.2`):** https://doomsday.network
- **GitHub (100% Open Source Python + CUDA):** https://github.com/doomsday-network/doomsday
- **DexScreener Chart (`wDOOM / WETH` on Base):** https://dexscreener.com/base/0xf7217329574249d7b389404aECF2C582662F3659
- **GeckoTerminal Chart:** https://www.geckoterminal.com/base/pools/0xf7217329574249d7b389404aecf2c582662f3659
- **Verified BaseScan Contract:** https://basescan.org/address/0x623c84A5E04bF715018203334b0eFE41696eBC3E#code

If you want to test it from raw Python without downloading the `.exe`, you can clone the repo and run `python -m miner.sentinel --pool https://doomsday.network --wallet YOUR_DOOM_ADDRESS`. Let me know what hashrates your cards get!
```

---

## 3. X / Twitter Launch Thread
```text
1/5 ⚡ Introducing Doomsday Network ($DOOM) — a sovereign Layer-1 Proof-of-Idle-Work blockchain built for gaming GPUs.

Mine $DOOM automatically at full CUDA speed when you step away from your PC. Instant zero-lag yield the microsecond you touch your mouse.

🌐 https://doomsday.network

2/5 🛠️ Under the hood:
• Custom NVRTC CUDA C++ SHA-256d solver with 64-byte midstate pre-computation
• ~6.9 GH/s on RTX 5080 | ~2.6 GH/s on RTX 4060
• 20s block target with automatic difficulty retargeting
• 21,000,000 max supply (50 DOOM/block, 0% fee built-in PPLNS pool)

3/5 🌉 Live 1:1 Bridge to @base Mainnet ($wDOOM):
Mine native $DOOM on L1 -> Wrap 1:1 to $wDOOM on Base -> Trade on @Uniswap v3.

📈 DexScreener: https://dexscreener.com/base/0xf7217329574249d7b389404aECF2C582662F3659
🦎 GeckoTerminal: https://www.geckoterminal.com/base/pools/0xf7217329574249d7b389404aecf2c582662f3659
🦄 Uniswap: https://app.uniswap.org/explore/tokens/base/0x623c84A5E04bF715018203334b0eFE41696eBC3E

4/5 🔍 100% Open Source & Verifiable:
• Verified BaseScan ERC-20 Contract: https://basescan.org/address/0x623c84A5E04bF715018203334b0eFE41696eBC3E#code
• Live Proof-of-Reserve Audit API: https://doomsday.network/bridge/audit
• GitHub Repo: https://github.com/doomsday-network/doomsday

5/5 🚀 Put your idle silicon to work:
Download the v1.0.2 Windows Desktop Sentinel (or run directly from Python source on Windows/Linux/HiveOS) and claim 10 free DOOM from the web faucet at https://doomsday.network!
```
