import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "components", "01-semantic-telemetry-otel"))
from jevlogs_triage import JevLogTriager
from jevmetrics_processor import JevMetricsProcessor
from jevtraces_tail_sampler import JevTraceSampler

class TestOtelProcessors(unittest.TestCase):
    def test_jevlogs_triage_error_vs_info(self):
        triager = JevLogTriager()
        err_record = {"severity_text": "FATAL", "body": "OutOfMemoryError in processing loop"}
        info_record = {"severity_text": "INFO", "body": "HTTP 200 OK GET /healthz"}

        res_err = triager.triage_record(err_record)
        res_info = triager.triage_record(info_record)

        self.assertEqual(res_err["route"], "warm_analysis")
        self.assertTrue(res_err["is_anomaly"])

        self.assertEqual(res_info["route"], "cold_archive")
        self.assertFalse(res_info["is_anomaly"])

    def test_jevmetrics_processor(self):
        proc = JevMetricsProcessor(mode="annotate")
        metric = {
            "name": "http_requests_total",
            "description": "Total HTTP requests",
            "unit": "1",
            "attributes": {"handler": "/checkout"}
        }
        result = proc.process_metric(metric)
        self.assertIn("jev.tier", result["attributes"])

    def test_jevtraces_tail_sampler(self):
        sampler = JevTraceSampler()
        trace = [
            {"trace_id": "abc123", "name": "POST /order", "status": {"code": "ERROR"}, "duration_ms": 1500}
        ]
        res = sampler.evaluate_trace(trace)
        self.assertEqual(res["action"], "retain_primary")

if __name__ == "__main__":
    unittest.main()
