#!/usr/bin/env python3
"""
DEMO 3: SRE Agent Dual-Loop Architecture.
Reference: SREGym Lite (sregym.com/blog/jev-sregym-lite)

Demonstrates:
1. Inner Loop (System 2): Open-ended reasoning and exploratory commands.
2. Second Loop (System 1): Continuous decision supervisor:
   - Ranks diagnostic tests.
   - Blocks premature diagnosis until evidence is mathematically sufficient.
   - Verifies whether repair telemetry confirms resolution before closing incident.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "components", "03-sre-agent-dual-loop"))
from sre_supervisor import SRESecondLoopSupervisor

def main():
    print("=" * 70)
    print(" JEVOPS DEMO 3: SRE AGENT DUAL-LOOP ARCHITECTURE ")
    print("=" * 70)

    supervisor = SRESecondLoopSupervisor()
    incident = "Kubernetes Pod auth-server-82x9c in CrashLoopBackOff with ExitCode 137"

    print(f"[*] Incident Detected:\n    \"{incident}\"\n")

    # Step 1: Hypothesis Ranking
    hypotheses = [
        "Network latency timeout to Redis cluster",
        "JVM heap memory exhaustion triggering Linux cgroup OOMKilled",
        "Missing TLS certificate mount on secret volume",
    ]
    print("[1] System 2 proposes 3 candidate hypotheses:")
    for h in hypotheses:
        print(f"    - {h}")

    ranked = supervisor.rank_diagnostic_hypotheses(incident, hypotheses)
    print("\n[+] System 1 Second Loop ranks diagnostic investigation order:")
    for rank, (hypo, score) in enumerate(ranked, 1):
        print(f"    {rank}. {hypo} (Relevance Score: {score:.3f})")

    # Step 2: Evidence Gating
    print("\n[2] System 2 attempts early diagnosis with incomplete evidence...")
    weak_evidence = ["Pod restart count is 14"]
    premature_check = supervisor.verify_evidence_before_diagnosis(
        incident_summary=incident,
        collected_evidence=weak_evidence,
        proposed_diagnosis="OOMKilled memory issue",
    )
    print(f"    - Evidence Sufficient: {premature_check['evidence_sufficient']}")
    print(f"    - Can Submit Diagnosis: {premature_check['can_submit_diagnosis']}")
    print(f"    - Supervisor Action:    {premature_check['recommendation']}")

    print("\n[3] System 2 collects conclusive evidence from dmesg and container status...")
    solid_evidence = [
        "kubectl describe pod: Last State Terminated Reason OOMKilled Exit Code 137",
        "dmesg: Memory cgroup out of memory: Killed process 4182 (java)",
        "Prometheus container_memory_working_set_bytes hit limit 512Mi",
    ]
    solid_check = supervisor.verify_evidence_before_diagnosis(
        incident_summary=incident,
        collected_evidence=solid_evidence,
        proposed_diagnosis="JVM process exceeded 512Mi cgroup limit and was terminated by kernel OOM killer",
    )
    print(f"    - Evidence Sufficient:  {solid_check['evidence_sufficient']}")
    print(f"    - Confidence:           {solid_check['confidence']:.2f}")
    print(f"    - Can Submit Diagnosis: {solid_check['can_submit_diagnosis']}")
    print(f"    - Supervisor Action:    {solid_check['recommendation']}")

    # Step 3: Mitigation Verification
    print("\n[4] System 2 applies mitigation (scaled container limit to 1.5Gi)...")
    post_telemetry = "Pod Running 1/1, memory stable at 610Mi, 0 restarts in 15m, HTTP /healthz 200 OK"
    mitigation_verif = supervisor.verify_mitigation_success(
        original_symptom=incident,
        repair_action_taken="Updated Deployment resource limits memory: 1536Mi",
        post_repair_telemetry=post_telemetry,
    )
    print(f"    - Resolution Verified:  {mitigation_verif['resolved']}")
    print(f"    - Operational Next Step: {mitigation_verif['next_step'].upper()}")

    print("\n[✔] Conclusion: The Dual-Loop architecture prevented premature false mitigation")
    print("    and verified production recovery in 3 discrete System 1 decision steps!")
    print("=" * 70)

if __name__ == "__main__":
    main()
