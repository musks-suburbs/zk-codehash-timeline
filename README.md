# zk-codehash-timeline

## Overview
**zk-codehash-timeline** samples a contract’s on-chain bytecode over a block range and reports a **timeline of code hashes** (keccak256 of bytecode).  
It detects potential **upgrades**, **proxy flips**, or **unsound changes** across time — useful for zk-focused systems like **Aztec** and **Zama**, where verifiers, bridges, and rollup components must remain consistent for proof soundness.

## Features
- Samples bytecode at configurable strides (e.g., every 500 blocks)
- Prints a readable timeline and highlights **change points**
- JSON output for CI pipelines and audit logs
- Exit code `2` when changes are detected (so monitoring can alert)
- Works on any EVM-compatible RPC (Ethereum, L2s, testnets)

## Installation
1. Python 3.9+
2. Install dependency:
   pip install web3
3. Set an RPC (or pass `--rpc`):
   export RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY

## Usage
Scan a contract every 500 blocks between two heights:
   python app.py --address 0xYourContract --from-block 19000000 --to-block 20000000 --step 500

Show **only change points** in the output:
   python app.py --address 0xYourContract --from-block 19000000 --to-block 20000000 --step 250 --only-changes

Use a custom RPC and emit JSON (for CI):
   python app.py --rpc https://arb1.arbitrum.io/rpc --address 0xYourContract --from-block 200000 --to-block 400000 --step 1000 --json

Tight scan for a sensitive verifier contract:
   python app.py --address 0xVerifier --from-block 0 --to-block 500000 --step 50

## Example Output
🔧 zk-codehash-timeline  
🧭 Chain ID: 1  
🔗 RPC: https://mainnet.infura.io/v3/…  
🏷️ Address: 0x00000000219ab540356cBB839Cbe05303d7705Fa  
🧱 Range: 19000000 → 19005000 (step=500)  
🔎 Checking block 19000000 ...  
🔎 Checking block 19000500 ...  
🔎 Checking block 19001000 ...  
📜 Timeline summary:  
  • #19000000: 0x5a3a64a28a59f47a3f1d...  
  • #19000500: 0x5a3a64a28a59f47a3f1d...  
  • #19001000: 0x9be1f0d0e3c1ab4470a0...  
  • #19001500: 0x9be1f0d0e3c1ab4470a0...  
🚨 Detected code hash changes over the scanned range.  
⏱️ Completed in 0.92s  

## Notes
- **Archive data:** Historical `get_code` requires an archive-capable RPC for older blocks. If your node doesn’t have history, some lookups may fail (the tool prints warnings).
- **Sampling vs. full scan:** Use a smaller `--step` for higher resolution (more RPC calls), or a larger `--step` for speed.
- **EOA / not yet deployed:** If no code exists at a block, the timeline shows “(no code)”.
- **CI semantics:** Exit code `0` means no changes were observed in the samples, `2` means changes were detected (or printed in JSON).
- **ZK relevance:** Stable code hashes improve **soundness** of zk proofs that assume fixed verification logic (e.g., rollup verifiers, bridge contracts, message inbox/outbox).
- **Cross-chain audits:** Run this tool on L1 and L2 copies of the same address to detect divergent deployments across time windows.

## Caveats
- Bytecode **equality** implies bit-for-bit match; identical logic compiled with different settings may still hash differently.
- Proxies: if scanning the **proxy address**, you’ll observe changes when the **implementation** behind the proxy changes (as expected). If you want to track the implementation directly, scan that address instead.

## Exit Codes
- `0` → No code hash changes detected (within sampled blocks)  
- `2` → Code hash changed at least once (or used for CI alerting)  
