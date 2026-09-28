# Build Stage / Universal Container Image
# Fully compatible with OpenShift 4.20+ restricted-v2 SCC, AKS, EKS, and GKE
FROM registry.access.redhat.com/ubi9/ubi-minimal:latest AS base

LABEL maintainer="nubenetes" \
      summary="Air-Gapped JevOps Decision Model Server" \
      description="Zero-egress local decision engine for OpenShift 4.20+, AKS, EKS, and GKE"

# Install Python 3.11 minimal runtime
RUN microdnf update -y && \
    microdnf install -y python3.11 python3.11-pip && \
    microdnf clean all && \
    rm -rf /var/cache/yum

WORKDIR /app

# Copy core package and server
COPY core /app/core
COPY airgap-decision-server /app/airgap-decision-server

ENV PYTHONPATH="/app/core:${PYTHONPATH}" \
    PORT=8080 \
    PYTHONUNBUFFERED=1

# OpenShift restricted-v2 security requirement: non-root UID
USER 10001:0

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz')" || exit 1

ENTRYPOINT ["python3.11", "/app/airgap-decision-server/server.py"]
