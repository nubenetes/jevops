#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONPATH="${REPO_ROOT}/core:${PYTHONPATH:-}"

echo -e "\033[1;36m"
cat <<'BANNER'
       __             ____             
      / /__ _   __  / __ \____  _____
 __  / / _ \ | / / / / / / __ \/ ___/
/ /_/ /  __/ |/ / / /_/ / /_/ (__  ) 
\____/\___/|___/  \____/ .___/____/  
                      /_/            
   Decision Models for Cloud Native DevOps
BANNER
echo -e "\033[0m"

echo -e "\033[1;32m>>> Running Demo 1: OpenTelemetry Log Triage Benchmark...\033[0m"
python3 "${SCRIPT_DIR}/demo1_otel_log_triage.py"
echo ""

echo -e "\033[1;32m>>> Running Demo 2: Kubernetes Semantic Action Gate (dsh-jev)...\033[0m"
python3 "${SCRIPT_DIR}/demo2_k8s_action_gate.py"
echo ""

echo -e "\033[1;32m>>> Running Demo 3: SRE Agent Dual-Loop Supervisor (SREGym Lite)...\033[0m"
python3 "${SCRIPT_DIR}/demo3_sre_dual_loop.py"
echo ""

echo -e "\033[1;32m>>> Running Demo 4: Semantic Canary Progressive Delivery & Rollback...\033[0m"
python3 "${SCRIPT_DIR}/demo4_canary_rollback.py"
echo ""

echo -e "\033[1;32m>>> Running Demo 5: Air-Gapped Zero-Egress & John Rood's Law...\033[0m"
python3 "${SCRIPT_DIR}/demo5_airgap_and_failover.py"
echo ""

echo -e "\033[1;35m======================================================================\033[0m"
echo -e "\033[1;32m  ALL 5 JEVOPS DEMOS EXECUTED SUCCESSFULLY!\033[0m"
echo -e "\033[1;35m======================================================================\033[0m"
