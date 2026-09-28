"""
CI Semantic Pathfinder: Intelligent Job & Test Selection.
Reference: jev-ci-pathfinder (jevlist.ai/projects/jev-ci-pathfinder)

Instead of running monolithic 2-hour CI suites on every pull request, or using
fragile glob file matchers:
1. Always-on critical jobs (linters, static security scans) remain strictly deterministic.
2. JevOps evaluates the semantic git diff against optional test suites.
3. Selects only relevant test targets (e.g., skips database migrations tests
   when only frontend CSS or README was modified).
"""

import sys
import os
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))
from jevops_core import (
    ChoiceQuestion,
    JevClient,
    NoulQuestion,
)


class CISemanticPathfinder:
    ALWAYS_ON_JOBS = ["lint", "secret-detection", "unit-tests-core"]

    OPTIONAL_JOBS = {
        "e2e-payment-gateway": "Runs full simulated credit card payment flows with sandbox banking APIs",
        "load-testing-k6": "Executes 10-minute 5,000 RPS load test on ingress endpoints",
        "db-migration-rollback-matrix": "Validates schema backward compatibility on PostgreSQL & MySQL",
        "frontend-visual-regression": "Runs Playwright pixel comparison across 12 screen resolutions",
        "airgap-ocp-validation": "Spins up disconnected OpenShift cluster simulation and tests zero-egress",
    }

    def __init__(self, client: JevClient = None):
        self.client = client or JevClient()

    def select_jobs(self, git_diff_summary: str, changed_files: List[str]) -> Dict[str, Any]:
        selected_jobs = list(self.ALWAYS_ON_JOBS)
        evaluated_jobs = {}

        questions = []
        for job_name, job_desc in self.OPTIONAL_JOBS.items():
            questions.append(
                NoulQuestion(
                    id=job_name,
                    prompt=f"Is the CI job '{job_name}' ({job_desc}) relevant to this code change?",
                    default=True,  # John Rood fallback: fail toward noise (run the test)
                )
            )

        context = (
            f"CHANGED_FILES: {changed_files}\n"
            f"GIT_DIFF_SUMMARY:\n{git_diff_summary}"
        )

        resp = self.client.decide(context=context, questions=questions)

        for job_name in self.OPTIONAL_JOBS.keys():
            noul_res = resp.get_noul(job_name)
            should_run = noul_res.value if noul_res else True
            evaluated_jobs[job_name] = {
                "run": should_run,
                "confidence": noul_res.confidence if noul_res else 1.0,
            }
            if should_run:
                selected_jobs.append(job_name)

        return {
            "total_available_jobs": len(self.ALWAYS_ON_JOBS) + len(self.OPTIONAL_JOBS),
            "selected_jobs_count": len(selected_jobs),
            "selected_jobs": selected_jobs,
            "evaluated_jobs": evaluated_jobs,
            "always_on": self.ALWAYS_ON_JOBS,
            "degraded": resp.degraded,
            "latency_ms": resp.latency_ms,
        }


if __name__ == "__main__":
    pathfinder = CISemanticPathfinder()

    # Scenario: A PR changing only database migration schemas
    diff = """
    diff --git a/migrations/0042_add_order_uuid_idx.sql b/migrations/0042_add_order_uuid_idx.sql
    + CREATE INDEX CONCURRENTLY idx_orders_customer_uuid ON orders (customer_uuid);
    + ALTER TABLE orders ADD COLUMN idempotency_key VARCHAR(64);
    """
    files = ["migrations/0042_add_order_uuid_idx.sql"]

    plan = pathfinder.select_jobs(diff, files)
    print("CI Pathfinder Selection:\n", plan)
