# app.py
import os
import sys
import json
import time
import argparse
from typing import Dict, List, Optional, Tuple
from web3 import Web3

DEFAULT_RPC = os.environ.get("RPC_URL", "https://mainnet.infura.io/v3/YOUR_INFURA_KEY")

def to_checksum(addr: str) -> str:
    if not Web3.is_address(addr):
        raise ValueError(f"Invalid Ethereum address: {addr}")
    return Web3.to_checksum_address(addr)

def codehash_at(w3: Web3, address: str, block_id: int) -> Optional[str]:
    """
    Return keccak256 hash of bytecode at a given block, or None if no code (EOA or not deployed yet).
    """
    try:
        code = w3.eth.get_code(address, block_identifier=block_id)
        if code is None or len(code) == 0:
            return None
        return Web3.keccak(code).hex()
    except Exception as e:
        # Some RPCs without archive support may fail for old blocks
        raise RuntimeError(f"get_code failed at block {block_id}: {e}")

def scan_codehash_timeline(
    w3: Web3,
    address: str,
    start_block: int,
    end_block: int,
    step: int,
    show_progress_every: int = 25,
) -> List[Tuple[int, Optional[str]]]:
    """
    Iterate blocks in [start_block, end_block] (inclusive) with the given step,
    returning (blockNumber, codeHashOrNone) timeline.
    """
    results: List[Tuple[int, Optional[str]]] = []
    last_progress = time.time()
    for idx, block in enumerate(range(start_block, end_block + 1, step), start=1):
        if time.time() - last_progress >= 0.2 or (idx % show_progress_every == 0):
            print(f"🔎 Checking block {block} ...")
            last_progress = time.time()
        try:
            h = codehash_at(w3, address, block)
        except Exception as e:
            print(f"⚠️  Block {block}: {e}")
            h = None
        results.append((block, h))
    return results

def summarize_changes(timeline: List[Tuple[int, Optional[str]]]) -> List[Tuple[int, Optional[str]]]:
    """
    From the full timeline, return only change points: first seen, and any time the hash differs from previous.
    """
    changes: List[Tuple[int, Optional[str]]] = []
    prev: Optional[str] = object()  # sentinel
    for block, h in timeline:
        if h != prev:
            changes.append((block, h))
            prev = h
    return changes

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="zk-codehash-timeline — track smart contract bytecode hash over time to detect upgrades or unsound changes (useful for Aztec/Zama bridges, verifiers, and Web3 audits)."
    )
    p.add_argument("--rpc", default=DEFAULT_RPC, help="EVM RPC URL (default from RPC_URL)")
    p.add_argument("--address", required=True, help="Contract address to track")
    p.add_argument("--from-block", type=int, required=True, help="Starting block (inclusive)")
    p.add_argument("--to-block", type=int, required=True, help="Ending block (inclusive)")
    p.add_argument("--step", type=int, default=500, help="Block stride for sampling (default: 500)")
    p.add_argument("--only-changes", action="store_true", help="Print only change points")
    p.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    p.add_argument("--timeout", type=int, default=30, help="RPC timeout seconds (default: 30)")
    return p.parse_args()

def main() -> None:
    args = parse_args()

    # Basic validation
    if not args.rpc.startswith(("http://", "https://")):
        print("❌ Invalid RPC URL. Must start with http(s).")
        sys.exit(1)
    if args.from_block > args.to_block:
        print("❌ --from-block must be <= --to-block")
        sys.exit(1)
    if args.step <= 0:
        print("❌ --step must be positive")
        sys.exit(1)

    try:
        address = to_checksum(args.address)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(args.rpc, request_kwargs={"timeout": args.timeout}))
    if not w3.is_connected():
        print("❌ RPC connection failed. Check --rpc or RPC_URL.")
        sys.exit(1)

    print("🔧 zk-codehash-timeline")
    try:
        print(f"🧭 Chain ID: {w3.eth.chain_id}")
    except Exception:
        pass
    print(f"🔗 RPC: {args.rpc}")
    print(f"🏷️ Address: {address}")
    print(f"🧱 Range: {args.from_block} → {args.to_block} (step={args.step})")

    t0 = time.time()
    timeline = scan_codehash_timeline(
        w3, address, args.from_block, args.to_block, args.step
    )
    changes = summarize_changes(timeline)
    elapsed = time.time() - t0

    print("📜 Timeline summary:")
    to_print = changes if args.only_changes else timeline
    for block, h in to_print:
        if h is None:
            print(f"  • #{block}: (no code)")
        else:
            print(f"  • #{block}: {h}")

    # Heuristic: if more than one unique non-None hash appears, consider "changed"
    unique_hashes = sorted({h for _, h in timeline if h is not None})
    changed = len(unique_hashes) > 1

    if changed:
        print("🚨 Detected code hash changes over the scanned range.")
    else:
        print("🎯 No code hash change detected in the scanned samples.")

    print(f"⏱️ Completed in {elapsed:.2f}s")

    if args.json:
        out: Dict[str, object] = {
            "rpc": args.rpc,
            "chain_id": None,
            "address": address,
            "from_block": args.from_block,
            "to_block": args.to_block,
            "step": args.step,
            "timeline": [{"block": b, "hash": h} for b, h in timeline],
            "change_points": [{"block": b, "hash": h} for b, h in changes],
            "unique_hashes": unique_hashes,
            "changed": changed,
            "elapsed_seconds": round(elapsed, 2),
        }
        try:
            out["chain_id"] = w3.eth.chain_id
        except Exception:
            pass
        print(json.dumps(out, ensure_ascii=False, indent=2))

    # Exit code: 0 if unchanged, 2 if changes detected (so CI can alert)
    sys.exit(2 if changed else 0)

if __name__ == "__main__":
    main()
