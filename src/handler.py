"""Done-claim checker: a small harness around one Bedrock model.

POST {"claim": "...", "evidence": "..."} and get back a verdict on whether the evidence
supports the claim. The harness does the parts a model should not be trusted with:

1. Budget guard: a per-day call counter in DynamoDB. Past DAILY_CAP the function refuses
   before it ever calls Bedrock, so a busy day cannot drain the account's credits.
2. Input limits: claim and evidence are capped in size; max output tokens is fixed.
3. Deterministic checks first: empty evidence, evidence with no concrete artifact
   (hash, URL, command output, timestamp, number), claim words the evidence never mentions.
4. One model, chosen at deploy time (MODEL_ID). No routing between models.
5. The model's answer is parsed and validated; anything that is not the expected JSON
   shape is reported as "unparseable", never passed through as a verdict.
"""
import json
import os
import re
import time

MAX_CLAIM = 600
MAX_EVIDENCE = 4000
MAX_TOKENS = 300
VERDICTS = {"supported", "partial", "unsupported"}

ARTIFACT_PATTERNS = [
    ("commit or hash", re.compile(r"\b[0-9a-f]{7,40}\b")),
    ("url", re.compile(r"https?://\S+")),
    ("timestamp", re.compile(r"\b\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2})?")),
    ("command output", re.compile(r"(^\$ |\bexit (code )?\d+\b|\bHTTP/\d(\.\d)? \d{3}\b|\b(PASS|FAIL|OK)\b)", re.M)),
    ("number", re.compile(r"\b\d+(\.\d+)?\b")),
]
STOP = set("the a an and or to of in on for is was are be been it this that with as by at from i we done "
           "complete completed finished successfully all now has have".split())


def deterministic_checks(claim, evidence):
    """Checks that need no model. Returns (blocking_problem or None, notes list, artifacts list)."""
    notes = []
    if not evidence.strip():
        return "no evidence given", notes, []
    artifacts = [name for name, rx in ARTIFACT_PATTERNS if rx.search(evidence)]
    if not artifacts:
        notes.append("evidence contains no concrete artifact (hash, URL, timestamp, command output, number)")
    claim_words = {w for w in re.findall(r"[a-z][a-z0-9_-]{2,}", claim.lower()) if w not in STOP}
    ev = evidence.lower()
    missing = sorted(w for w in claim_words if w not in ev)
    if claim_words and len(missing) / len(claim_words) > 0.6:
        notes.append("most claim terms never appear in the evidence: " + ", ".join(missing[:8]))
    return None, notes, artifacts


def build_prompt(claim, evidence):
    return (
        "You check whether evidence supports a claim that some work is done.\n"
        "Judge only from the evidence text. Do not assume anything not shown.\n"
        'Reply with JSON only: {"verdict": "supported"|"partial"|"unsupported", '
        '"missing": [short strings], "reason": "one sentence"}\n\n'
        f"CLAIM:\n{claim}\n\nEVIDENCE:\n{evidence}\n"
    )


def parse_model_reply(text):
    """Accept only the exact shape we asked for."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except ValueError:
        return None
    if obj.get("verdict") not in VERDICTS or not isinstance(obj.get("reason"), str):
        return None
    missing = obj.get("missing", [])
    if not isinstance(missing, list) or not all(isinstance(x, str) for x in missing):
        return None
    return {"verdict": obj["verdict"], "missing": missing[:10], "reason": obj["reason"][:300]}


def take_budget(ddb, table, cap, now=None):
    """Atomically count one call for today; False when the daily cap is reached."""
    day = time.strftime("%Y-%m-%d", time.gmtime(now or time.time()))
    try:
        ddb.update_item(
            TableName=table,
            Key={"pk": {"S": f"day#{day}"}},
            UpdateExpression="ADD calls :one SET expires_at = if_not_exists(expires_at, :ttl)",
            ConditionExpression="attribute_not_exists(calls) OR calls < :cap",
            ExpressionAttributeValues={":one": {"N": "1"}, ":cap": {"N": str(cap)},
                                       ":ttl": {"N": str(int((now or time.time()) + 8 * 86400))}},
        )
        return True
    except ddb.exceptions.ConditionalCheckFailedException:
        return False


def respond(status, body):
    return {"statusCode": status, "headers": {"content-type": "application/json"}, "body": json.dumps(body)}


def check(claim, evidence, ddb, bedrock, table, cap, model_id):
    claim, evidence = (claim or "").strip(), (evidence or "")
    if not claim:
        return 400, {"error": "claim is required"}
    if len(claim) > MAX_CLAIM or len(evidence) > MAX_EVIDENCE:
        return 413, {"error": f"limits: claim {MAX_CLAIM} chars, evidence {MAX_EVIDENCE} chars"}
    blocking, notes, artifacts = deterministic_checks(claim, evidence)
    if blocking:
        return 200, {"verdict": "unsupported", "reason": blocking, "checks": notes, "model_called": False}
    if not take_budget(ddb, table, cap):
        return 429, {"error": "daily budget reached; try tomorrow", "model_called": False}
    out = bedrock.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": build_prompt(claim, evidence)}]}],
        inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0},
    )
    text = "".join(c.get("text", "") for c in out["output"]["message"]["content"])
    parsed = parse_model_reply(text)
    usage = out.get("usage", {})
    if parsed is None:
        return 200, {"verdict": "unparseable", "checks": notes, "artifacts": artifacts, "model_called": True,
                     "model": model_id, "usage": usage}
    if notes and parsed["verdict"] == "supported":
        parsed["verdict"] = "partial"
        parsed["reason"] = "model said supported, but deterministic checks flagged: " + "; ".join(notes)
    return 200, {**parsed, "checks": notes, "artifacts": artifacts, "model_called": True,
                 "model": model_id, "usage": usage}


def lambda_handler(event, context):
    import boto3  # imported lazily so unit tests need no AWS SDK

    try:
        body = json.loads(event.get("body") or "{}")
    except ValueError:
        return respond(400, {"error": "body must be JSON"})
    status, payload = check(
        body.get("claim"), body.get("evidence"),
        boto3.client("dynamodb"), boto3.client("bedrock-runtime"),
        os.environ["BUDGET_TABLE"], int(os.environ.get("DAILY_CAP", "100")), os.environ["MODEL_ID"],
    )
    return respond(status, payload)
