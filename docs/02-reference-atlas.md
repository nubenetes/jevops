# Reference Atlas: Deconstructing the 12 JevOps Projects

This document provides a comprehensive technical examination of every reference and community project cited in Josh Rosen's foundational article.

---

## 1. Cribl AI Research: Decision Models in Telemetry
- **Citation**: [Cribl AI Research Blog (Sep 2026)](https://cribl.io/blog/what-typesafes-jev-means-for-telemetry/)
- **Core Problem**: Modern observability pipelines ingest terabytes of events daily. Decisions regarding parser selection, PII masking, alert routing, schema inference, and LLM judge evals were historically either too rigid (regex) or too expensive to run continuously.
- **Architectural Breakthrough**: Cribl benchmarked Jev against an LLM-as-a-judge committee. Jev achieved **92% agreement with the LLM committee at 1% of the cost**.
- **JevOps Implementation**: Implemented in [`components/01-semantic-telemetry-otel/`](../components/01-semantic-telemetry-otel/).

---

## 2. Jev Logs (`reachjalil/jevlogs`) & HDFS/BGL Benchmark
- **Citation**: [jevlogs.com](https://jevlogs.com/) | [HuggingFace Benchmark](https://huggingface.co/datasets/reachjalil/jevlogs-log-triage-benchmark) | [npm package](https://github.com/reachjalil/jevlogs)
- **Core Problem**: Streaming logs to high-cost analytics backends (Elasticsearch, Datadog, Loki) causes ballooning storage bills.
- **Architectural Breakthrough**: Wraps an OpenTelemetry Log Exporter. Every log record still travels to the cold archive, but Jev evaluates diagnostic relevance in real-time.
- **Benchmark Metrics**: Tested on sanitized supercomputer (BGL) and distributed filesystem (HDFS) logs:
  - **99.3% anomaly recall on HDFS**
  - **100% anomaly recall on BGL**
  - **Filtered >99% of routine noise**.
- **JevOps Implementation**: Verified in [`components/01-semantic-telemetry-otel/jevlogs_triage.py`](../components/01-semantic-telemetry-otel/jevlogs_triage.py) and [`demos/demo1_otel_log_triage.py`](../demos/demo1_otel_log_triage.py).

---

## 3. Jevernetes (`jevlist.ai/projects/jevernetes`)
- **Citation**: [Jevernetes](https://jevlist.ai/projects/jevernetes)
- **Core Problem**: Live Kubernetes logs are noisy. Operators and coding agents need immediate surrounding context when an anomaly occurs.
- **Architectural Breakthrough**: Highlights events deserving investigation, computes local context windows, and produces evidence packets for autonomous coding agents, with offline keyword fallbacks.
- **JevOps Implementation**: Incorporated in [`core/jevops_core/local_engine.py`](../core/jevops_core/local_engine.py).

---

## 4. JevBrief (`jevbrief`)
- **Citation**: [PyPI: jevbrief/0.1.0](https://pypi.org/project/jevbrief/0.1.0/)
- **Core Problem**: Sending 10,000 raw logs to an LLM blows through token budgets and causes attention degradation.
- **Architectural Breakthrough**: Takes 1,447 OpenTelemetry log records, groups them into 23 semantic clusters, narrows to 5 top anomaly candidates, and asks Jev: *"Which evidence candidate best explains the incident?"*
- **JevOps Implementation**: [`components/01-semantic-telemetry-otel/jevbrief_compressor.py`](../components/01-semantic-telemetry-otel/jevbrief_compressor.py).

---

## 5. JevMetrics (`ishantanu/jevmetrics`)
- **Citation**: [ishantanu/jevmetrics](https://github.com/ishantanu/jevmetrics)
- **Core Problem**: High-cardinality metrics create massive TSDB churn before dashboards or queries are even established.
- **Architectural Breakthrough**: Custom OTel Collector processor that queries Jev on instrument metadata (name, description, unit, attribute keys).
- **Modes**:
  - `annotate`: Tags metrics with semantic metadata without dropping.
  - `route`: Directs SLO-critical metrics to Prometheus/Mimir and non-critical metrics to rollups.
  - `reduce`: Drops high-cardinality volatile labels (`user_id`, `client_ip`) from low-value metrics.
- **JevOps Implementation**: [`components/01-semantic-telemetry-otel/jevmetrics_processor.py`](../components/01-semantic-telemetry-otel/jevmetrics_processor.py).

---

## 6. JevTraces (`ishantanu/jevtraces`)
- **Citation**: [ishantanu/jevtraces](https://github.com/ishantanu/jevtraces)
- **Core Problem**: Fixed-rate head sampling drops critical error traces, while naive tail sampling retains too much redundant data.
- **Architectural Breakthrough**: Evaluates trace spans for diagnostic utility and business criticality. Integrates with OpenTelemetry tail sampling while routing full streams to cold archives.
- **JevOps Implementation**: [`components/01-semantic-telemetry-otel/jevtraces_tail_sampler.py`](../components/01-semantic-telemetry-otel/jevtraces_tail_sampler.py).

---

## 7. Datadog Agent Observability: Evals as Operational Signals
- **Citation**: [Datadog Blog (Sep 2026)](https://www.datadoghq.com/blog/jev-evals-agent-observability/)
- **Core Problem**: LLM-as-a-judge traditionally runs offline hours after execution.
- **Architectural Breakthrough**: Jev evaluates production agent spans *as they arrive* in real time. It answers focused questions: Are claims supported? Did a policy violation occur? Is human review needed? These evaluations are attached directly to span telemetry.
- **JevOps Implementation**: Supported across the SDK and OTel collector pipelines.

---

## 8. SREGym Lite: SRE Agents in a Second Loop
- **Citation**: [SREGym Blog](https://sregym.com/blog/jev-sregym-lite)
- **Core Problem**: Autonomous SRE agents running System 2 reasoning models waste tokens debating diagnostic priorities and prematurely declare incidents solved.
- **Architectural Breakthrough**: **Dual-Loop Architecture**:
  - Inner Loop: System 2 reasoning model investigates and explores.
  - Second Loop: System 1 decision model continuously ranks candidate diagnostic tests, checks evidence sufficiency, and gates mitigation declarations.
  - **Results**: Benchmark success rate improved from **40% (20/50) to 48% (24/50)**.
- **JevOps Implementation**: [`components/03-sre-agent-dual-loop/`](../components/03-sre-agent-dual-loop/) and [`demos/demo3_sre_dual_loop.py`](../demos/demo3_sre_dual_loop.py).

---

## 9. Semantic Gates on Actions (`dsh-jev`)
- **Citation**: [buberlo/dsh-jev (DeepSeek Harness)](https://github.com/buberlo/dsh-jev)
- **Core Problem**: Standard Kubernetes RBAC validates *permission*, not *operational sanity*. An agent permitted to modify NetworkPolicies might open `0.0.0.0/0` across port 5432 to restore connectivity, exposing production databases.
- **Architectural Breakthrough**: Semantic Action Gate intercepts proposed Kubernetes mutations and evaluates them against active incident context before execution.
- **JevOps Implementation**: [`components/02-k8s-semantic-action-gate/`](../components/02-k8s-semantic-action-gate/) and [`demos/demo2_k8s_action_gate.py`](../demos/demo2_k8s_action_gate.py).

---

## 10. Incident Response Decomposition (`jev-oncall`, `typesafe-jev-incident-router`, SecOps)
- **Citations**:
  - [jev-oncall](https://jevcases.com/cases/jev-oncall/)
  - [typesafe-jev-incident-router (kyle-chalmers)](https://github.com/kyle-chalmers/typesafe-jev-incident-router)
  - [kenhuangus/jev-usecases](https://github.com/kenhuangus/jev-usecases)
- **Core Problem**: Treating incident response as a single monolithic generative prompt leads to hallucinations, unbounded latency, and operational unpredictability.
- **Architectural Breakthrough**: Decomposes incident response into staged, confidence-gated micro-decisions:
  - Triage -> Route -> Containment Gate -> Mitigation Verification -> Recovery.
  - High confidence executes automatically; low confidence escalates safely to human triage queues.
- **JevOps Implementation**: [`components/05-incident-decomposition/`](../components/05-incident-decomposition/).

---

## 11. CI and Semantic Selection (`jev-ci-pathfinder`)
- **Citation**: [jev-ci-pathfinder](https://jevlist.ai/projects/jev-ci-pathfinder)
- **Core Problem**: Monolithic CI pipelines waste compute running unneeded integration tests for minor markdown or schema changes. Brittle path filters miss cross-cutting regressions.
- **Architectural Breakthrough**: Deterministic jobs (linting, secret scans) stay in code; Jev semantically evaluates the git diff against allowlisted integration test targets.
- **JevOps Implementation**: [`components/06-ci-semantic-pathfinder/`](../components/06-ci-semantic-pathfinder/).

---

## 12. Progressive Delivery & Deployment State Machines (Temporal & Canary Demos)
- **Citations**:
  - [Jev Deployment State Machine](https://stacktoheap.com/demos/jev-deployment-state-machine/)
  - [thenoahhein/jev-temporal-demo](https://github.com/thenoahhein/jev-temporal-demo)
- **Core Problem**: Rigid static thresholds (`error_rate > 1%`) fail to capture multi-dimensional canary health.
- **Architectural Breakthrough**: Combines deterministic orchestration (Argo Rollouts, Temporal) with semantic evaluation:
  - Jev evaluates canary health at transition points: `HOLD`, `PROMOTE`, or `ROLLBACK`.
  - Temporal handles retries and durable state without asking Jev to re-make decisions.
- **JevOps Implementation**: [`components/04-progressive-delivery/`](../components/04-progressive-delivery/) and [`demos/demo4_canary_rollback.py`](../demos/demo4_canary_rollback.py).
