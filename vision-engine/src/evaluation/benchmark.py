"""Benchmark models for latency, throughput, and resource usage."""

import os
import time
from pathlib import Path

import numpy as np


def benchmark_model(
    weights_path: str,
    device: str = "cpu",
    img_size: int = 640,
    warmup_runs: int = 50,
    benchmark_runs: int = 200,
) -> dict:
    """Measure inference latency and throughput.

    Returns:
        Dict with mean_latency_ms, p95_latency_ms, fps, model_size_mb, params
    """
    from ultralytics import YOLO

    model = YOLO(weights_path)

    dummy_input = np.random.randint(0, 255, (img_size, img_size, 3), dtype=np.uint8)

    for _ in range(warmup_runs):
        model(dummy_input, device=device, verbose=False)

    latencies = []
    for _ in range(benchmark_runs):
        start = time.perf_counter()
        model(dummy_input, device=device, verbose=False)
        elapsed = (time.perf_counter() - start) * 1000
        latencies.append(elapsed)

    latencies_np = np.array(latencies)
    mean_latency = float(np.mean(latencies_np))
    p95_latency = float(np.percentile(latencies_np, 95))
    fps = 1000.0 / mean_latency if mean_latency > 0 else 0

    model_size = os.path.getsize(weights_path) / (1024 * 1024) if Path(weights_path).exists() else 0

    param_count = sum(p.numel() for p in model.model.parameters())

    return {
        "mean_latency_ms": round(mean_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "fps": round(fps, 1),
        "model_size_mb": round(model_size, 2),
        "parameters": param_count,
        "device": device,
        "img_size": img_size,
        "warmup_runs": warmup_runs,
        "benchmark_runs": benchmark_runs,
    }
