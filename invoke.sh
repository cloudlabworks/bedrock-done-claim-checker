#!/usr/bin/env bash
# Exercise the deployed function directly (works with the private URL): one weak claim, one strong claim.
set -u
cd "$(dirname "$0")" || exit 1
export AWS_REGION="${AWS_REGION:-us-east-1}" AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
STACK="${STACK_NAME:-bedrock-harness-demo}"
. lib/cfn.sh
FN=$(stack_output "$STACK" FunctionName)
call() {
  python3 -c 'import json,sys;print(json.dumps({"body":json.dumps({"claim":sys.argv[1],"evidence":sys.argv[2]})}))' "$1" "$2" > build/event.json
  aws lambda invoke --function-name "$FN" --cli-binary-format raw-in-base64-out --payload fileb://build/event.json build/out.json >/dev/null \
    && python3 -c 'import json;r=json.load(open("build/out.json"));print(r["statusCode"], json.dumps(json.loads(r["body"]),indent=1))'
}
echo "== weak: claim with no evidence artifacts"
call "Migrated the database and rotated all keys" "It went fine."
echo "== strong: claim with hash, test output, timestamp"
call "Deployed v2 and the tests passed" $'$ git log -1\nabc1234 deploy v2\n$ pytest\n12 passed, exit 0\n2026-10-27 13:40 deploy ok'
