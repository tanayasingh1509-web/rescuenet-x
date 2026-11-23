#!/usr/bin/env python3
"""
RESCUENET-X Reproducible Performance Benchmark
Measures actual inference and routing latency:
1. Audio STT latency on a 3-second audio sample
2. Vision inference time (Color/edge heuristic + YOLO person detection)
3. Routing & urgency computation time
Outputs results to benchmarks.json and frontend/public/benchmarks.json.
"""

import os
import sys
import time
import json
import wave
import io
import platform
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set yolo config dir safely
os.environ.setdefault("YOLO_CONFIG_DIR", str(PROJECT_ROOT / ".ultralytics"))

def generate_sample_wav(duration_sec=3.0, sample_rate=16000) -> bytes:
    """Generate a clean synthetic 3-second 16kHz PCM mono WAV in memory."""
    import math
    import struct

    num_samples = int(duration_sec * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # 440 Hz gentle sine tone
        frames = []
        for i in range(num_samples):
            val = int(12000 * math.sin(2 * math.pi * 440 * (i / sample_rate)))
            frames.append(struct.pack('<h', val))
        wf.writeframes(b''.join(frames))
    return buf.getvalue()

def benchmark_routing():
    """Benchmark end-to-end agentic dispatch pipeline (dedup, urgency scoring, unit routing)."""
    from backend.agentic_dispatcher import run_agentic_pipeline
    from backend.store import store
    from backend.schemas import EventPayload

    event = EventPayload(
        id="BENCH_01",
        category="FLOOD",
        sector="Sector 18",
        severity=8,
        casualty_count=2,
        coordinates={"lat": 28.6145, "lng": 77.2085},
        summary="Flood evacuation required",
        confidence=0.88,
        source="voice",
        raw_transcript="Water rising rapidly",
        verified=False
    )

    times = []
    # Warmup
    for _ in range(3):
        store.reset()
        run_agentic_pipeline(event)

    for i in range(15):
        store.reset()
        t0 = time.perf_counter()
        run_agentic_pipeline(event)
        times.append((time.perf_counter() - t0) * 1000.0)

    avg_ms = sum(times) / len(times)
    min_ms = min(times)
    p95_ms = sorted(times)[int(len(times) * 0.95)]
    return {
        "avg_ms": round(avg_ms, 3),
        "min_ms": round(min_ms, 3),
        "p95_ms": round(p95_ms, 3),
        "iterations": len(times)
    }

def benchmark_stt():
    """Benchmark STT latency on a 3-second audio sample."""
    from backend.ai_engine import process_audio_transcript

    wav_bytes = generate_sample_wav(duration_sec=3.0)
    audio_path = PROJECT_ROOT / "backend" / "audio_samples" / "benchmark_sample.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audio_path, "wb") as f:
        f.write(wav_bytes)

    times = []
    # 3 iterations
    for _ in range(3):
        t0 = time.perf_counter()
        result = process_audio_transcript(str(audio_path))
        elapsed = (time.perf_counter() - t0) * 1000.0
        times.append(elapsed)

    if audio_path.exists():
        audio_path.unlink()

    avg_ms = sum(times) / len(times)
    return {
        "sample_duration_s": 3.0,
        "avg_ms": round(avg_ms, 2),
        "p95_ms": round(sorted(times)[-1], 2),
        "iterations": len(times),
        "transcript_preview": result.get("transcript", "")[:50]
    }

def benchmark_vision():
    """Benchmark vision inference (Color/edge heuristic + person counting)."""
    from backend.vision_engine import analyze_visual_disaster
    from PIL import Image

    test_img_path = PROJECT_ROOT / "backend" / "audio_samples" / "bench_image.jpg"
    img = Image.new('RGB', (640, 480), color=(220, 80, 20))
    img.save(test_img_path)

    times = []
    # Warmup
    analyze_visual_disaster(str(test_img_path))

    for _ in range(5):
        t0 = time.perf_counter()
        res = analyze_visual_disaster(str(test_img_path))
        times.append((time.perf_counter() - t0) * 1000.0)

    if test_img_path.exists():
        test_img_path.unlink()

    avg_ms = sum(times) / len(times)
    return {
        "avg_ms": round(avg_ms, 2),
        "min_ms": round(min(times), 2),
        "p95_ms": round(sorted(times)[-1], 2),
        "iterations": len(times),
        "detected_category": res.get("category")
    }

def main():
    print("=" * 60)
    print("RESCUENET-X BENCHMARK SUITE")
    print(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {platform.python_version()}")
    print("=" * 60)

    print("\n[1/3] Benchmarking Routing & Dispatch Engine...")
    routing_results = benchmark_routing()
    print(f"  -> Routing Latency: {routing_results['avg_ms']} ms (avg across {routing_results['iterations']} runs)")

    print("\n[2/3] Benchmarking Vision Inference Engine...")
    vision_results = benchmark_vision()
    print(f"  -> Vision Latency: {vision_results['avg_ms']} ms (avg)")

    print("\n[3/3] Benchmarking STT Pipeline (3.0s sample)...")
    stt_results = benchmark_stt()
    print(f"  -> STT Latency: {stt_results['avg_ms']} ms (avg)")

    benchmark_data = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "os": platform.system(),
            "python": platform.python_version(),
            "architecture": platform.machine()
        },
        "routing": routing_results,
        "vision": vision_results,
        "stt": stt_results
    }

    out_file = PROJECT_ROOT / "benchmarks.json"
    with open(out_file, "w") as f:
        json.dump(benchmark_data, f, indent=2)
    print(f"\nSaved benchmark results to {out_file}")

    public_dir = PROJECT_ROOT / "frontend" / "public"
    if public_dir.exists():
        frontend_out = public_dir / "benchmarks.json"
        with open(frontend_out, "w") as f:
            json.dump(benchmark_data, f, indent=2)
        print(f"Saved copy to {frontend_out}")

    print("\n✅ Benchmark run completed successfully.")

if __name__ == "__main__":
    main()
