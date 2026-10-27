#!/usr/bin/env bash
# Before deploying: prove this account can call the chosen model at all (Free-plan accounts may not reach
# every Bedrock model). One tiny call, 20 output tokens max.
set -u
export AWS_REGION="${AWS_REGION:-us-east-1}" AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
MODEL="${MODEL_ID:-amazon.nova-micro-v1:0}"
echo "== one test call to $MODEL in $AWS_REGION"
aws bedrock-runtime converse --model-id "$MODEL" \
  --messages '[{"role":"user","content":[{"text":"Reply with the single word: ready"}]}]' \
  --inference-config '{"maxTokens":20,"temperature":0}' \
  --query '{text: output.message.content[0].text, usage: usage}' --output json \
  && echo "PREFLIGHT OK" || { echo "PREFLIGHT FAILED: model not callable from this account/region" >&2; exit 1; }
