# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

#!/bin/bash

set -euo pipefail

echo "Deploy principal and relate aproxy"
terraform apply -auto-approve
juju deploy ubuntu --channel=latest/stable --model tf-testing-lxd
juju integrate ubuntu aproxy --model tf-testing-lxd

echo "Wait for aproxy to be deployed"
juju wait-for application aproxy --query='status=="maintenance" || status=="blocked"' --timeout=10m

echo "Verify aproxy application is deployed"
STATUS=$(juju status aproxy --model tf-testing-lxd --format=json | jq -r '.applications.aproxy["application-status"].current')
echo "aproxy status: $STATUS"
if [ "$STATUS" == "error" ] || [ "$STATUS" == "unknown" ]; then
	echo "aproxy failed to deploy or is unknown"
	juju status --model test-aproxy-example
	exit 1
fi
