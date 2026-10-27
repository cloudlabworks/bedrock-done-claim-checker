#!/usr/bin/env bash
# Deploy the stack (private URL by default), then upload src/handler.py as the function code.
set -u
cd "$(dirname "$0")" || exit 1
export AWS_REGION="${AWS_REGION:-us-east-1}" AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
STACK="${STACK_NAME:-bedrock-harness-demo}"
. lib/cfn.sh
./preflight.sh || exit 1
echo "== deploying stack $STACK in $AWS_REGION"
aws cloudformation deploy --stack-name "$STACK" --template-file bedrock-harness-demo.yaml \
  --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset \
  --parameter-overrides ModelId="${MODEL_ID:-amazon.nova-micro-v1:0}" DailyCap="${DAILY_CAP:-100}" UrlAuthType="${URL_AUTH:-AWS_IAM}" || exit 1
FN=$(stack_output "$STACK" FunctionName)
echo "== packaging src/handler.py -> build/checker.zip (as index.py)"
rm -rf build && mkdir -p build && cp src/handler.py build/index.py && (cd build && python3 -m zipfile -c checker.zip index.py) || exit 1
aws lambda update-function-code --function-name "$FN" --zip-file fileb://build/checker.zip --query LastUpdateStatus --output text || exit 1
aws lambda wait function-updated --function-name "$FN" || exit 1
aws cloudformation describe-stacks --stack-name "$STACK" --query 'Stacks[0].Outputs' --output table
echo "Next: ./invoke.sh"
