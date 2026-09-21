"""AI Service — Performance Benchmark for CP3.

Measures:
  - Concurrent request handling (100 users)
  - P99 latency
  - Error rate
  - Cost tracking accuracy
"""
from __future__ import annotations

import asyncio
import time
import statistics
from typing import Any


async def benchmark_concurrent_requests(num_users: int = 100, duration_s: float = 30.0) -> dict[str, Any]:
    """Simulate concurrent users making requests."""
    from services.ai.agent.memory import MemoryManager
    from services.ai.model.quota import TenantQuotaManager
    from services.ai.model.cost import CostTracker

    # Initialize components
    memory = MemoryManager(tenant_id="benchmark-tenant")
    quota = TenantQuotaManager(redis_url="redis://localhost:9999")
    cost = CostTracker()

    latencies = []
    errors = 0
    start = time.perf_counter()
    end = start + duration_s
    completed = 0

    async def worker(worker_id: int) -> None:
        nonlocal completed, errors
        while time.perf_counter() < end:
            t0 = time.perf_counter()
            try:
                # Simulate agent memory operations
                memory.add_to_short_term("user", f"Query from worker {worker_id}")
                memory.add_to_short_term("assistant", f"Response for worker {worker_id}")
                memory.get_short_term()

                # Simulate quota check
                result = await quota.check_and_consume(
                    tenant_id="benchmark-tenant",
                    model="gpt-4o",
                    provider="openai",
                    prompt_tokens=100,
                    completion_tokens=50,
                )

                # Simulate cost tracking
                cost.track_usage(
                    tenant_id="benchmark-tenant",
                    model="gpt-4o",
                    provider="openai",
                    input_tokens=100,
                    output_tokens=50,
                    cost_usd=0.0005,
                )

                latencies.append((time.perf_counter() - t0) * 1000)
                completed += 1
            except Exception as e:
                errors += 1

    # Launch concurrent workers
    tasks = [asyncio.create_task(worker(i)) for i in range(num_users)]
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start

    # Calculate metrics
    if latencies:
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
        avg = statistics.mean(latencies)
    else:
        p50 = p95 = p99 = avg = 0.0

    error_rate = errors / completed if completed > 0 else 0.0
    throughput = completed / elapsed if elapsed > 0 else 0.0

    return {
        "num_users": num_users,
        "duration_s": elapsed,
        "completed_requests": completed,
        "throughput_req_per_sec": throughput,
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "latency_p99_ms": p99,
        "error_rate": error_rate,
        "total_errors": errors,
    }


async def benchmark_cost_tracking() -> dict[str, Any]:
    """Verify cost tracking accuracy."""
    from services.ai.model.cost import CostTracker

    cost = CostTracker()
    tenant_id = "cost-test-tenant"

    # Track several requests
    test_cases = [
        {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "expected_cost": 0.00035},
        {"model": "gpt-4o-mini", "input_tokens": 200, "output_tokens": 100, "expected_cost": 0.000045},
        {"model": "llama3.2", "input_tokens": 150, "output_tokens": 75, "expected_cost": 0.0},
    ]

    total_expected = 0.0
    for case in test_cases:
        cost.track_usage(
            tenant_id=tenant_id,
            model=case["model"],
            provider="openai" if case["model"].startswith("gpt") else "ollama",
            input_tokens=case["input_tokens"],
            output_tokens=case["output_tokens"],
            cost_usd=case["expected_cost"],
        )
        total_expected += case["expected_cost"]

    # Verify total cost
    total_actual = await cost.get_total_cost(tenant_id)
    accuracy = abs(total_actual - total_expected) / total_expected if total_expected > 0 else 0.0

    return {
        "total_expected_usd": total_expected,
        "total_actual_usd": total_actual,
        "accuracy": 1.0 - accuracy,
        "all_costs_accurate": accuracy < 0.01,
    }


async def main() -> None:
    """Run all benchmarks."""
    print("=" * 60)
    print("DT-Lite AI Service — Performance Benchmark")
    print("=" * 60)

    # Benchmark 1: Concurrent requests
    print("\n[1] Concurrent Request Benchmark (100 users, 30s)...")
    bench1 = await benchmark_concurrent_requests(num_users=100, duration_s=30.0)
    print(f"  Completed: {bench1['completed_requests']} requests")
    print(f"  Throughput: {bench1['throughput_req_per_sec']:.1f} req/s")
    print(f"  P50 Latency: {bench1['latency_p50_ms']:.1f} ms")
    print(f"  P95 Latency: {bench1['latency_p95_ms']:.1f} ms")
    print(f"  P99 Latency: {bench1['latency_p99_ms']:.1f} ms")
    print(f"  Error Rate: {bench1['error_rate']:.2%}")

    # Benchmark 2: Cost tracking accuracy
    print("\n[2] Cost Tracking Accuracy Benchmark...")
    bench2 = await benchmark_cost_tracking()
    print(f"  Expected Cost: ${bench2['total_expected_usd']:.6f}")
    print(f"  Actual Cost: ${bench2['total_actual_usd']:.6f}")
    print(f"  Accuracy: {bench2['accuracy']:.2%}")
    print(f"  All Accurate: {'YES' if bench2['all_costs_accurate'] else 'NO'}")

    # Summary
    print("\n" + "=" * 60)
    all_pass = (
        bench1['error_rate'] < 0.001 and
        bench1['latency_p99_ms'] < 2000 and
        bench2['all_costs_accurate']
    )
    if all_pass:
        print("[PASS] All benchmarks passed")
    else:
        print("[WARN] Some benchmarks did not meet targets")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
