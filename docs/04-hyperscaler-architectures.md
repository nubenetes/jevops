# Hyperscaler Reference Architectures: AKS, EKS, and GKE

| [← Prev: **03. Air-Gap OpenShift 4.20+**](03-airgap-openshift-4-20.md) | [🏠 **Home (README)**](../README.md) | [Next: **05. Resilience & Fallbacks** →](05-resilience-and-fallbacks.md) |
| :--- | :---: | ---: |

This guide provides deployment patterns and blueprints for running JevOps across the major public cloud managed Kubernetes services.

---

## 1. Azure Kubernetes Service (AKS)

### Identity & Secrets
- Uses **Azure Workload Identity** to eliminate static cloud credentials.
- The Kubernetes ServiceAccount is annotated with the Azure Client ID ([`deploy/aks/workload-identity.yaml`](../deploy/aks/workload-identity.yaml)):
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jevops-sa
  namespace: jevops-system
  annotations:
    azure.workload.identity/client-id: "<AZURE_CLIENT_ID>"
```

### Telemetry Pipeline
- Integrates with Azure Monitor OpenTelemetry Collector DaemonSet ([`deploy/aks/azure-monitor-otel.yaml`](../deploy/aks/azure-monitor-otel.yaml)) to route triaged traces and logs to Azure Log Analytics.

---

## 2. Amazon Elastic Kubernetes Service (EKS)

### Identity & Secrets
- Uses **EKS Pod Identity** or **IAM Roles for Service Accounts (IRSA)** ([`deploy/eks/pod-identity-irsa.yaml`](../deploy/eks/pod-identity-irsa.yaml)).
- Decider API keys are mounted directly via AWS Secrets Manager CSI driver.

### Telemetry Pipeline
- Uses **AWS Distro for OpenTelemetry (ADOT)** ([`deploy/eks/adot-collector.yaml`](../deploy/eks/adot-collector.yaml)):
  - Retained diagnostic traces route to AWS X-Ray.
  - Metrics route to Amazon Managed Service for Prometheus (AMP).

---

## 3. Google Kubernetes Engine (GKE)

### Identity & Secrets
- Uses **GKE Workload Identity Federation** ([`deploy/gke/workload-identity.yaml`](../deploy/gke/workload-identity.yaml)):
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jevops-sa
  namespace: jevops-system
  annotations:
    iam.gke.io/gcp-service-account: "jevops-decider@PROJECT_ID.iam.gserviceaccount.com"
```

### Telemetry Pipeline
- Integrates with Google Cloud Managed Service for Prometheus (GMP) using `PodMonitoring` custom resources ([`deploy/gke/gmp-otel-config.yaml`](../deploy/gke/gmp-otel-config.yaml)).

---

## 4. Multi-Cloud Feature Matrix

| Feature | OpenShift 4.20+ | AKS | EKS | GKE |
| :--- | :--- | :--- | :--- | :--- |
| **Security Standard** | `restricted-v2` SCC | Azure Policy | Pod Security Standards | PSS Restricted |
| **Identity Federation** | OpenShift ServiceAccount Tokens | Azure Workload Identity | EKS Pod Identity / IRSA | GKE Workload Identity |
| **Telemetry Collector** | Red Hat OpenTelemetry Operator | Azure Monitor OTel | AWS ADOT Collector | GMP + Cloud Trace |
| **Air-Gap Capable** | **Native (oc-mirror v2)** | Restricted Virtual Networks | Isolated VPC Enclaves | Private GKE Clusters |
| **Helm Values Profile** | `--set global.platform=openshift-airgap` | `--set global.platform=aks` | `--set global.platform=eks` | `--set global.platform=gke` |

---

| [← Prev: **03. Air-Gap OpenShift 4.20+**](03-airgap-openshift-4-20.md) | [🏠 **Home (README)**](../README.md) | [Next: **05. Resilience & Fallbacks** →](05-resilience-and-fallbacks.md) |
| :--- | :---: | ---: |

