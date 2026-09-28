"""
Air-Gapped Decision Model Server.

Runs as a container sidecar or cluster daemonset.
Exposes standard System 1 API:
- POST /v1/systemone
- GET /healthz
- GET /readyz

Supports both standalone standard-library HTTP server (zero external dependencies)
and high-throughput FastAPI/Uvicorn if installed.
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict

# Ensure local core package is accessible
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from jevops_core import (
    ChoiceQuestion,
    DecisionBatchRequest,
    LocalDecisionEngine,
    NoulQuestion,
    ScoreQuestion,
)

engine = LocalDecisionEngine()


class AirgapHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path in ("/healthz", "/readyz", "/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "mode": "airgap"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/v1/systemone":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                context = payload.get("context", "")
                raw_questions = payload.get("questions", [])

                questions = []
                for q in raw_questions:
                    q_type = q.get("type", "choice")
                    q_id = q.get("id", "q1")
                    q_prompt = q.get("prompt", "")
                    if q_type == "choice":
                        questions.append(
                            ChoiceQuestion(
                                id=q_id,
                                prompt=q_prompt,
                                options=q.get("options", []),
                                default=q.get("default"),
                            )
                        )
                    elif q_type == "score":
                        questions.append(
                            ScoreQuestion(
                                id=q_id,
                                prompt=q_prompt,
                                min_value=float(q.get("min_value", 0.0)),
                                max_value=float(q.get("max_value", 1.0)),
                                default=q.get("default"),
                            )
                        )
                    elif q_type == "noul":
                        questions.append(
                            NoulQuestion(
                                id=q_id,
                                prompt=q_prompt,
                                default=q.get("default"),
                            )
                        )

                req = DecisionBatchRequest(context=context, questions=questions)
                resp = engine.execute_batch(req)

                # Format response payload
                res_dict: Dict[str, Any] = {}
                for k, v in resp.results.items():
                    if hasattr(v, "selected"):
                        res_dict[k] = {
                            "selected": v.selected,
                            "confidence": v.confidence,
                            "probabilities": v.probabilities,
                        }
                    elif hasattr(v, "score"):
                        res_dict[k] = {
                            "score": v.score,
                            "confidence": v.confidence,
                        }
                    elif hasattr(v, "value"):
                        res_dict[k] = {
                            "value": v.value,
                            "probability": v.probability,
                            "confidence": v.confidence,
                        }

                response_payload = {
                    "results": res_dict,
                    "latency_ms": resp.latency_ms,
                    "degraded": False,
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_payload).encode("utf-8"))

            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_server(port: int = 8080):
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, AirgapHTTPRequestHandler)
    print(f"JevOps Air-Gapped Decision Server listening on port {port}")
    httpd.serve_forever()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    run_server(port)
