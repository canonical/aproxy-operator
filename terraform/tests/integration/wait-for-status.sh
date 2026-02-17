#!/bin/bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

MODEL_UUID=$1

juju wait-for application aproxy --query='status=="maintenance" || status=="blocked"' --timeout=10m &> /dev/null
STATUS=$(juju status aproxy --model "$MODEL_UUID" --format=json | jq -r '.applications.aproxy["application-status"].current')

echo '{"status": "'$STATUS'"}'
