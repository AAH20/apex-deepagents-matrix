"""Benchmark suite for apex-deepagents-matrix optimization kernels."""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apex_deepagents_matrix.solvers import (
    AllocationItem,
    KnapsackResourceAllocator,
    ScheduledTask,
    TopologicalTaskScheduler,
)


def main() -> None:
    print("=" * 72)
    print(" apex-deepagents-matrix: Microsecond Solver Benchmark Suite")
    print(" Pure Python 3.10+ Standard Library — Zero External Dependencies")
    print("=" * 72)

    # Benchmark 1: Knapsack Allocator on 100 candidate tasks
    items = [AllocationItem(item_id=f"gpu_task_{i}", weight=(i % 10) + 1, value=float((i % 25) + 10)) for i in range(100)]
    capacity = 150

    print(f"[*] Benchmarking 5,000 Knapsack Resource Allocations (100 items each)...")
    t0 = time.perf_counter()
    for _ in range(5000):
        KnapsackResourceAllocator.allocate(items, capacity)
    total_ms = (time.perf_counter() - t0) * 1000.0
    avg_us = (total_ms / 5000) * 1000.0

    print(f"[+] Total execution time: {total_ms:.2f} ms")
    print(f"[+] Average allocation latency: {avg_us:.2f} µs ({avg_us / 1000.0:.4f} ms)")
    assert avg_us < 1000.0, "Latency exceeds 1ms threshold"
    print("[✔] SUB-MILLISECOND ALLOCATION THRESHOLD SATISFIED.")

    # Benchmark 2: Topological Task Scheduling across 500 tasks
    tasks = [
        ScheduledTask(
            task_id=f"task_{i:04d}",
            duration_estimate=1.0 + (i % 5),
            dependencies=[f"task_{(i - 1):04d}"] if i > 0 and i % 3 == 0 else [],
        )
        for i in range(500)
    ]
    print(f"\n[*] Benchmarking 1,000 Topological DAG Scheduling Cycles (500 tasks each)...")
    t0_sched = time.perf_counter()
    for _ in range(1000):
        TopologicalTaskScheduler.schedule(tasks)
    total_sched_ms = (time.perf_counter() - t0_sched) * 1000.0
    avg_sched_us = (total_sched_ms / 1000) * 1000.0

    print(f"[+] Total execution time: {total_sched_ms:.2f} ms")
    print(f"[+] Average scheduling latency: {avg_sched_us:.2f} µs ({avg_sched_us / 1000.0:.4f} ms)")
    assert avg_sched_us < 1000.0, "Latency exceeds 1ms threshold"
    print("[✔] SUB-MILLISECOND SCHEDULING THRESHOLD SATISFIED.")
    print("=" * 72)


if __name__ == "__main__":
    main()
