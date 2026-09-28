"""
Kubernetes Validating Admission Webhook Server.
Enforces semantic action gating at Kubernetes admission time.
Compatible with OpenShift 4.20+, AKS, EKS, and GKE.
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict

from gatekeeper_evaluator import SemanticActionGate

gate = SemanticActionGate()


class AdmissionWebhookHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == "/validate":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                review = json.loads(body)
                req = review.get("request", {})
                uid = req.get("uid", "")
                resource_kind = req.get("kind", {}).get("kind", "")
                resource_name = req.get("name", "unnamed")
                namespace = req.get("namespace", "default")
                proposed_object = req.get("object", {})

                # Context retrieved from cluster annotation or default incident state
                annotations = proposed_object.get("metadata", {}).get("annotations", {})
                incident_context = annotations.get(
                    "jevops.io/incident-context",
                    "Routine operational maintenance or autonomous SRE mitigation"
                )

                eval_result = gate.evaluate_mutation(
                    incident_context=incident_context,
                    target_resource=f"{resource_kind}/{namespace}/{resource_name}",
                    proposed_action_manifest=proposed_object,
                )

                admission_response = {
                    "apiVersion": "admission.k8s.io/v1",
                    "kind": "AdmissionReview",
                    "response": {
                        "uid": uid,
                        "allowed": eval_result["allowed"],
                        "status": {
                            "code": 200 if eval_result["allowed"] else 403,
                            "message": eval_result["reason"],
                        },
                    },
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(admission_response).encode("utf-8"))

            except Exception as e:
                # Fail safe: block mutation on webhook parsing error
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path in ("/healthz", "/readyz"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"healthy"}')
        else:
            self.send_response(404)
            self.end_headers()


def run(port: int = 8443):
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, AdmissionWebhookHandler)
    print(f"JevOps Semantic Admission Webhook running on port {port}")
    httpd.serve_forever()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8443"))
    run(port)
