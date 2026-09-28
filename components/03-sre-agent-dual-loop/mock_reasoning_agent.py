"""
Simulated Inner Reasoning Agent supervised by JevOps Second Loop.
Demonstrates the interaction between System 2 reasoning and System 1 gating.
"""

from sre_supervisor import SRESecondLoopSupervisor


class ReasoningSREAgent:
    def __init__(self, supervisor: SRESecondLoopSupervisor = None):
        self.supervisor = supervisor or SRESecondLoopSupervisor()
        self.evidence_log = []

    def troubleshoot(self, incident: str) -> str:
        print(f"\n[Inner Loop (System 2)] Starting investigation for: {incident}")

        # Step 1: Generate initial hypotheses
        hypotheses = [
            "Network egress packet drop to payment broker",
            "JVM heap exhaustion OOMKilled",
            "Invalid TLS certificate expired on upstream",
        ]
        print(f"[Inner Loop] Hypotheses: {hypotheses}")

        # Step 2: Second Loop ranks which test to execute first
        ranked = self.supervisor.rank_diagnostic_hypotheses(incident, hypotheses)
        print(f"[Second Loop (System 1)] Ranked priority: {ranked[0][0]} (score: {ranked[0][1]:.3f})")

        # Step 3: Gather evidence
        self.evidence_log.append("Pod terminated with exit code 137")
        self.evidence_log.append("Kernel cgroup memory controller invoked OOM killer")
        print(f"[Inner Loop] Gathered evidence: {self.evidence_log}")

        # Step 4: Gate diagnosis with Second Loop
        proposed_diag = "JVM memory leak triggering Linux kernel cgroup OOMKill"
        gate_check = self.supervisor.verify_evidence_before_diagnosis(
            incident_summary=incident,
            collected_evidence=self.evidence_log,
            proposed_diagnosis=proposed_diag,
        )
        print(f"[Second Loop (System 1)] Diagnosis Verification: {gate_check}")

        if not gate_check["can_submit_diagnosis"]:
            return "Investigation aborted: insufficient evidence."

        # Step 5: Execute remediation and verify
        remediation = "Scaled container memory limits from 512Mi to 2Gi"
        post_telemetry = "Pod healthy, memory usage stabilized at 820Mi, 0 restarts in 10 minutes"
        mitigation_check = self.supervisor.verify_mitigation_success(
            original_symptom=incident,
            repair_action_taken=remediation,
            post_repair_telemetry=post_telemetry,
        )
        print(f"[Second Loop (System 1)] Mitigation Check: {mitigation_check}")

        return "Incident Successfully Resolved and Verified by Dual-Loop Architecture."


if __name__ == "__main__":
    agent = ReasoningSREAgent()
    res = agent.troubleshoot("Auth Service Pod crashing continuously with OOMKilled exit code 137")
    print("\nResult:", res)
