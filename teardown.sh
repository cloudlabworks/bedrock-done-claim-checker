#!/usr/bin/env bash
# Delete everything this project created and prove it is gone.
set -u
cd "$(dirname "$0")" || exit 1
export AWS_REGION="${AWS_REGION:-us-east-1}" AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
STACK="${STACK_NAME:-bedrock-harness-demo}"
. lib/cfn.sh
delete_stack_and_wait "$STACK" && stack_gone "$STACK" && log_group_gone "/aws/lambda/${STACK}-checker"
