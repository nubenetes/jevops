# Enterprise Guide: Deploying JevOps on Red Hat OpenShift 4.20+

This guide details the deployment of JevOps across **Red Hat OpenShift 4.20+**, with specific focus on **on-premises air-gapped / disconnected enclaves** as well as managed cloud variants (ROSA, ARO, and OpenShift on GCP).

---

## 1. The Air-Gapped Challenge

Enterprise datacenters, defense enclaves, and regulated financial environments running OpenShift 4.20+ operate under strict **zero-egress** mandates:
- No internet access to external SaaS API endpoints (`https://api.typesafe.ai`).
- Strict container image mirroring via disconnected registries (Quay / Artifactory / Red Hat Mirror Registry).
- Compliance with OpenShift `restricted-v2` Security Context Constraints (SCC).

### The JevOps Dual-Mode Solution
JevOps provides a **Local Decision Engine Container**:
- A drop-in, zero-egress container sidecar or cluster daemonset.
- Serves the exact `POST /v1/systemone` OpenAPI contract locally with <5ms latency.
- Ships on `registry.access.redhat.com/ubi9/ubi-minimal`.
- Requires zero external network calls.

```mermaid
graph LR
    subgraph "OpenShift 4.20+ Air-Gapped Enclave"
        OTEL[OpenShift Logging / OTel Collector] -->|Local HTTP:8080| DEC[JevOps Local Decision Engine<br/>UBI9 Minimal | SCC restricted-v2]
        K8S_ADM[K8s API Server] -->|ValidatingWebhook| GATE[JevOps Semantic Action Gate]
        GATE -->|Local IPC/HTTP| DEC
    end

    subgraph "External World (Blocked)"
        SAAS[api.typesafe.ai]
    end

    DEC -.->|BLOCKED BY ZERO-EGRESS| SAAS
```

---

## 2. Red Hat SecurityContextConstraints (`restricted-v2`) Compliance

OpenShift 4.20+ enforces `restricted-v2` as the default SCC. All JevOps containers adhere strictly to these constraints:

```yaml
securityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
containers:
  - name: decision-engine
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
          - ALL
    volumeMounts:
      - name: tmp-volume
        mountPath: /tmp
```

---

## 3. Disconnected Image Mirroring with `oc-mirror` v2

To transfer JevOps images across the air-gap into your disconnected registry:

1. Define the `ImageSetConfiguration` ([`deploy/openshift-4.20/oc-mirror-imageset.yaml`](../deploy/openshift-4.20/oc-mirror-imageset.yaml)):
```bash
oc-mirror --config deploy/openshift-4.20/oc-mirror-imageset.yaml file://mirror-archive
```
2. Physically transfer the archive into the air-gapped network.
3. Push to your internal OpenShift Quay registry:
```bash
oc-mirror --from file://mirror-archive docker://internal-registry.corp.local/jevops
```

---

## 4. Disconnected Zero-Egress Network Isolation

Apply the strict NetworkPolicy ([`deploy/openshift-4.20/network-policy.yaml`](../deploy/openshift-4.20/network-policy.yaml)):
```bash
oc apply -f deploy/openshift-4.20/network-policy.yaml
```
This guarantees:
- Pods cannot open egress connections to external IP blocks.
- CoreDNS (port 53) and intra-cluster OTel streams are strictly whitelisted.

---

## 5. Public Cloud OpenShift (ROSA, ARO, GCP)

For managed OpenShift clusters in public clouds:
- **ROSA (Red Hat OpenShift on AWS)**: Use AWS Secrets Manager and STS assume-role for TypeSafe API credentials.
- **ARO (Azure Red Hat OpenShift)**: Use Azure Key Vault Provider and Managed Identity.
- Set `JEVOPS_MODE=cloud` and configure your egress firewall / proxy:
```bash
oc set env deployment/jevops-decision-engine -n jevops-system \
  JEVOPS_MODE=cloud \
  TYPESAFE_API_KEY="sk-..." \
  HTTPS_PROXY="http://corp-proxy.local:8080"
```
