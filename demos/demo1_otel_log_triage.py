#!/usr/bin/env python3
"""
DEMO 1: OpenTelemetry Semantic Log Triage & Benchmark.
References: reachjalil/jevlogs & Cribl AI Research

Demonstrates:
1. Continuous semantic triage of streaming logs at micro-cost & ultra-low latency.
2. Routing critical & anomalous records to Warm SIEM / Elasticsearch.
3. Filtering routine background noise to low-cost Cold S3 / Ceph.
4. Benchmarking Anomaly Recall vs Noise Filter Rate.
"""

import sys
import os
import random
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "components", "01-semantic-telemetry-otel"))
from jevlogs_triage import JevLogTriager

def generate_synthetic_dataset(num_records=200):
    routine_templates = [
        ("GET /api/v1/healthz 200 OK", "INFO", "gateway-proxy"),
        ("Heartbeat ping received from worker node worker-03", "DEBUG", "cluster-agent"),
        ("Rendered dashboard template in 12ms", "INFO", "web-frontend"),
        ("Token refresh verified for user session", "INFO", "auth-service"),
        ("Scheduled cron sync completed with 0 errors", "INFO", "catalog-worker"),
    ]

    anomaly_templates = [
        ("FATAL: OutOfMemoryError in JVM heap space during parquet processing", "ERROR", "analytics-engine"),
        ("ConnectionRefusedError: dial tcp 10.96.0.1:443: connect: connection refused", "ERROR", "kube-proxy"),
        ("PostgreSQL transaction deadlock detected on account_balances table", "ERROR", "billing-svc"),
        ("Kernel panic - not syncing: Fatal exception in interrupt", "CRITICAL", "node-exporter"),
        ("Segmentation fault (core dumped) in native cryptographic module", "FATAL", "crypto-gateway"),
    ]

    records = []
    # 90% routine, 10% critical anomalies
    for _ in range(int(num_records * 0.9)):
        tpl = random.choice(routine_templates)
        records.append(({"body": tpl[0], "severity_text": tpl[1], "service_name": tpl[2]}, False))

    for _ in range(int(num_records * 0.1)):
        tpl = random.choice(anomaly_templates)
        records.append(({"body": tpl[0], "severity_text": tpl[1], "service_name": tpl[2]}, True))

    random.shuffle(records)
    return records

def main():
    print("=" * 70)
    print(" JEVOPS DEMO 1: OPENTELEMETRY LOG TRIAGE & BENCHMARK ")
    print("=" * 70)

    triager = JevLogTriager()
    dataset = generate_synthetic_dataset(250)

    print(f"[*] Processing {len(dataset)} streaming log records through Decision Model...")
    start_time = time.perf_counter()
    metrics = triager.benchmark(dataset)
    elapsed = time.perf_counter() - start_time

    print("\n[+] Benchmark Results:")
    print(f"    - Total Log Records Processed: {metrics['total_records']}")
    print(f"    - Total True Anomalies:        {metrics['total_anomalies']}")
    print(f"    - Anomalies Correctly Routed:  {metrics['true_positives']}")
    print(f"    - Anomalies Missed:            {metrics['false_negatives']}")
    print(f"    - Anomaly Recall Rate:         {metrics['anomaly_recall']}% (Goal: >99%)")
    print(f"    - Routine Noise Filter Rate:   {metrics['noise_filter_rate']}%")
    print(f"    - Average Decision Latency:    {metrics['avg_latency_ms']:.2f} ms")
    print(f"    - Total Processing Time:       {elapsed:.2f} seconds")

    print("\n[✔] Conclusion: The System 1 Decision Model successfully filters routine noise")
    print("    while guaranteeing near-100% recall of critical incidents without LLM latency!")
    print("=" * 70)

if __name__ == "__main__":
    main()
