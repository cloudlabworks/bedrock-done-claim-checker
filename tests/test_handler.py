import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import handler  # noqa: E402


class CondFail(Exception):
    pass


class FakeDdb:
    class exceptions:
        ConditionalCheckFailedException = CondFail

    def __init__(self, cap_hit=False):
        self.calls, self.cap_hit = 0, cap_hit

    def update_item(self, **kw):
        if self.cap_hit:
            raise CondFail()
        self.calls += 1
        assert kw["ConditionExpression"].startswith("attribute_not_exists(calls) OR calls < :cap")


class FakeBedrock:
    def __init__(self, reply):
        self.reply, self.n = reply, 0

    def converse(self, **kw):
        self.n += 1
        assert kw["inferenceConfig"]["maxTokens"] == handler.MAX_TOKENS
        return {"output": {"message": {"content": [{"text": self.reply}]}}, "usage": {"inputTokens": 10}}


GOOD = json.dumps({"verdict": "supported", "missing": [], "reason": "hash and test output shown"})
EVID = "$ git log -1\nabc1234 deploy\n$ pytest\n12 passed, exit 0\n2026-10-27 13:40 deploy ok"


def run(claim, evidence, reply=GOOD, cap_hit=False):
    ddb, br = FakeDdb(cap_hit), FakeBedrock(reply)
    status, body = handler.check(claim, evidence, ddb, br, "t", 5, "amazon.nova-micro-v1:0")
    return status, body, ddb, br


class Tests(unittest.TestCase):
    def test_empty_evidence_never_calls_model(self):
        s, b, ddb, br = run("deployed the stack", "")
        self.assertEqual((s, b["verdict"], br.n, ddb.calls), (200, "unsupported", 0, 0))

    def test_missing_claim(self):
        self.assertEqual(run("", "x")[0], 400)

    def test_size_limits(self):
        self.assertEqual(run("a" * 601, "x")[0], 413)
        self.assertEqual(run("ok", "x" * 4001)[0], 413)

    def test_budget_cap_refuses_before_model(self):
        s, b, ddb, br = run("deploy pytest passed", EVID, cap_hit=True)
        self.assertEqual((s, br.n), (429, 0))

    def test_supported_with_artifacts(self):
        s, b, ddb, br = run("deploy done, pytest passed", EVID)
        self.assertEqual((s, b["verdict"], br.n, ddb.calls), (200, "supported", 1, 1))
        self.assertIn("commit or hash", b["artifacts"])

    def test_model_supported_downgraded_when_checks_flag(self):
        s, b, *_ = run("migrated database and rotated keys", "it went fine, trust me")
        self.assertEqual(b["verdict"], "partial")
        self.assertTrue(b["checks"])

    def test_unparseable_model_reply_is_not_a_verdict(self):
        s, b, *_ = run("deploy pytest passed", EVID, reply="Sure! Looks done to me.")
        self.assertEqual(b["verdict"], "unparseable")

    def test_bad_verdict_value_rejected(self):
        bad = json.dumps({"verdict": "probably", "missing": [], "reason": "x"})
        self.assertEqual(run("deploy pytest passed", EVID, reply=bad)[1]["verdict"], "unparseable")

    def test_reply_wrapped_in_prose_still_parsed(self):
        s, b, *_ = run("deploy pytest passed", EVID, reply="Here you go:\n" + GOOD + "\nThanks")
        self.assertEqual(b["verdict"], "supported")

    def test_missing_list_capped(self):
        many = json.dumps({"verdict": "partial", "missing": [str(i) for i in range(30)], "reason": "x"})
        self.assertEqual(len(run("deploy pytest passed", EVID, reply=many)[1]["missing"]), 10)


if __name__ == "__main__":
    unittest.main()
