#!/bin/bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd $DIR

set -euo pipefail

# Additional deployment tests for aproxy-operator
# This script contains additional tests extracted from the original workflow.

echo "Running additional deployment tests..."

juju integrate ubuntu aproxy --model tf-testing-lxd
juju wait-for application aproxy --query='status=="maintenance" || status=="blocked"' --timeout=10m
echo "aproxy status: $STATUS"
if [ "$STATUS" == "error" ] || [ "$STATUS" == "unknown" ]; then
  echo "aproxy failed to deploy or is unknown"
  juju status --model tf-testing-lxd
  exit 1
fi

echo "Additional tests completed successfully."
