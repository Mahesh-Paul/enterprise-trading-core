"""
infra/build_hooks/prewarm_cache.py

Build-time optimization hook executed during Docker container assembly.
Attempts to allocate a monolithic, un-paged Level-3 order book cache in RAM.

================================================================================
BUG #1: OUT-OF-MEMORY (OOM) CRASH DURING BUILD PHASE
================================================================================
During Docker image build (`RUN python -m infra.build_hooks.prewarm_cache`),
this script attempts to allocate a massive 128 GB memory buffer to cache static
tick ladders. On standard build hosts with container cgroup limits (or standard
developer machines), this triggers a MemoryError or the Linux Kernel OOM Killer
(SIGKILL 137), fatally aborting the container build.
================================================================================
"""

import os
import sys


def allocate_l3_depth_tables():
    print("=" * 75)
    print("  HFT MATCHING ENGINE: BUILD-TIME L3 CACHE PRE-ALLOCATION")
    print("=" * 75)

    target_gb = int(os.environ.get("PREALLOCATE_MARKET_DEPTH_GB", "128"))
    print(f"[*] Target Pre-Allocation Volume: {target_gb} GB RAM")
    print(f"[*] Instantiating 500,000 tick price-depth ladders across 500 trading pairs...")

    allocated_blocks = []
    chunk_size = 1024 * 1024 * 1024  # 1 Gigabyte per allocation unit

    try:
        for gb_idx in range(1, target_gb + 1):
            print(f"[*] [PAGE-MAPPING] Allocating L3 Depth Memory Chunk {gb_idx}/{target_gb} GB...", flush=True)
            # Allocate 1GB bytearray and write boundary bytes to force physical page faulting
            block = bytearray(chunk_size)
            block[0] = 0xAA
            block[chunk_size // 2] = 0x55
            block[-1] = 0xFF
            allocated_blocks.append(block)

        print(f"[✓] Successfully allocated {target_gb} GB memory.")
    except (MemoryError, OSError) as mem_err:
        print("\n" + "!" * 75, file=sys.stderr)
        print("  [FATAL ERROR] OUT-OF-MEMORY (OOM) TRIGGERED DURING BUILD PHASE", file=sys.stderr)
        print("!" * 75, file=sys.stderr)
        print(f"System Error: {mem_err}", file=sys.stderr)
        print(f"Failed at chunk index: {gb_idx} of {target_gb} GB.", file=sys.stderr)
        print("Docker container daemon / Linux cgroup OOM Killer terminated build process.", file=sys.stderr)
        print("Container Build Failure: Process exited with status 137 (SIGKILL)", file=sys.stderr)
        print("!" * 75, file=sys.stderr)
        sys.exit(137)


if __name__ == "__main__":
    allocate_l3_depth_tables()

