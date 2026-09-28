import re
"""
SRE Agent Second Loop Supervisor.
Reference: SREGym Lite (sregym.com/blog/jev-sregym-lite)

Dual-Loop Architecture:
- Inner Loop: System 2 Reasoning Model performs deep, open-ended investigation,
  runs commands, and proposes mitigations.
- Second Loop: System 1 Decision Model continuously watches the investigation,
  ranks diagnostic tests, verifies evidence sufficiency, and gates mitigation.
"""

import sys
import os
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))
from jevops_core import (
    ChoiceQuestion,
    JevClient,
    NoulQuestion,
    ScoreQuestion,
)


class SRESecondLoopSupervisor:
    def __init__(self, client: JevClient = None):
        self.client = client or JevClient()

    def rank_diagnostic_hypotheses(
        self,
        observed_symptoms: str,
        candidate_hypotheses: List[str],
    ) -> List[Tuple[str, float]]:
        """
        Ranks which diagnostic hypothesis should be investigated first.
        """
        if not candidate_hypotheses:
            return []

        context = (
            f"OBSERVED_SYMPTOMS: {observed_symptoms}\n"
            f"CANDIDATES: {candidate_hypotheses}"
        )

        questions = [
            ChoiceQuestion(
                id="top_hypothesis",
                prompt="Select the most probable root cause hypothesis to investigate first",
                options=candidate_hypotheses,
                default=candidate_hypotheses[0],
            )
        ]

        resp = self.client.decide(context=context, questions=questions)
        choice_res = resp.get_choice("top_hypothesis")

        # Extract probabilities
        probs = choice_res.probabilities if choice_res else {h: 1.0 / len(candidate_hypotheses) for h in candidate_hypotheses}
        ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
        return ranked

    def verify_evidence_before_diagnosis(
        self,
        incident_summary: str,
        collected_evidence: List[str],
        proposed_diagnosis: str,
    ) -> Dict[str, Any]:
        """
        Gates the reasoning agent from declaring diagnosis prematurely.
        """
        context = (
            f"INCIDENT: {incident_summary}\n"
            f"COLLECTED_EVIDENCE:\n" + "\n".join(f"- {e}" for e in collected_evidence) + "\n"
            f"PROPOSED_DIAGNOSIS: {proposed_diagnosis}"
        )

        questions = [
            NoulQuestion(
                id="is_evidence_sufficient",
                prompt="Does the collected evidence conclusively prove the proposed diagnosis?",
                default=False,  # Cautious default
            ),
            ScoreQuestion(
                id="diagnosis_confidence",
                prompt="Rate confidence that proposed diagnosis is correct based solely on evidence",
                min_value=0.0,
                max_value=1.0,
                default=0.5,
            ),
        ]

        resp = self.client.decide(context=context, questions=questions)
        suff_res = resp.get_noul("is_evidence_sufficient")
        conf_res = resp.get_score("diagnosis_confidence")

        # Semantic alignment between evidence and proposed diagnosis
        evidence_text = " ".join(collected_evidence).lower()
        diag_tokens = [t for t in re.findall(r"\w+", proposed_diagnosis.lower()) if len(t) > 3]
        matches = sum(1 for t in diag_tokens if t in evidence_text)
        token_overlap = matches / max(1, len(diag_tokens))
        
        # Grounding: sufficient if multiple pieces of evidence corroborate the diagnosis tokens
        sufficient = (len(collected_evidence) >= 2 and token_overlap >= 0.3)
        confidence = round(min(0.98, max(0.4, 0.4 + token_overlap * 0.6)), 2)

        return {
            "can_submit_diagnosis": sufficient and confidence >= 0.75,
            "evidence_sufficient": sufficient,
            "confidence": confidence,
            "recommendation": (
                "Proceed with mitigation" if (sufficient and confidence >= 0.75)
                else "Collect additional telemetry evidence before acting"
            ),
            "latency_ms": resp.latency_ms,
        }

    def verify_mitigation_success(
        self,
        original_symptom: str,
        repair_action_taken: str,
        post_repair_telemetry: str,
    ) -> Dict[str, Any]:
        """
        Validates whether the repair actually solved the problem.
        """
        context = (
            f"ORIGINAL_SYMPTOM: {original_symptom}\n"
            f"REPAIR_ACTION: {repair_action_taken}\n"
            f"POST_REPAIR_TELEMETRY: {post_repair_telemetry}"
        )

        questions = [
            NoulQuestion(
                id="is_incident_resolved",
                prompt="Has the incident been conclusively mitigated based on post-repair telemetry?",
                default=False,
            ),
            ChoiceQuestion(
                id="next_step",
                prompt="Determine operational next step",
                options=["close_incident", "continue_troubleshooting", "escalate_to_human"],
                default="continue_troubleshooting",
            ),
        ]

        resp = self.client.decide(context=context, questions=questions)
        resolved_res = resp.get_noul("is_incident_resolved")
        step_res = resp.get_choice("next_step")

        return {
            "resolved": resolved_res.value if resolved_res else False,
            "next_step": step_res.selected if step_res else "continue_troubleshooting",
            "confidence": resolved_res.confidence if resolved_res else 1.0,
            "latency_ms": resp.latency_ms,
        }


if __name__ == "__main__":
    supervisor = SRESecondLoopSupervisor()

    symptoms = "Kubernetes Pod payment-gateway in CrashLoopBackOff with ExitCode 137"
    hypotheses = [
        "Memory OOMKilled exceeding container limit",
        "Liveness probe HTTP timeout due to slow DB",
        "Misconfigured secret mounted to nonexistent path",
    ]

    ranked = supervisor.rank_diagnostic_hypotheses(symptoms, hypotheses)
    print("Ranked Hypotheses:", ranked)

    verif = supervisor.verify_evidence_before_diagnosis(
        incident_summary=symptoms,
        collected_evidence=[
            "kubectl describe pod confirms Last State: Terminated with Exit Code 137",
            "dmesg log shows 'Memory cgroup out of memory: Killed process 8421'",
        ],
        proposed_diagnosis="Container exceeded memory limit of 512Mi and was OOMKilled by kernel",
    )
    print("\nEvidence Verification:", verif)
