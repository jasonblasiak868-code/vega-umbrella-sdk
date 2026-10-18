"""Functional tests for the umbrella: registry, one-organism assembly across the other SDKs, and the audit gate."""
import copy
import hashlib
import json
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import fixture_umbrella as fx  # noqa: E402
from vega_umbrella import audit, registry  # noqa: E402


class Registry(unittest.TestCase):
    def test_the_real_family_is_sound(self):
        self.assertTrue(registry.check_registry())
        order = registry.build_order()
        self.assertEqual(order[0], "vega-custody-sdk")
        self.assertLess(order.index("vega-harness-sdk"), order.index("vega-council-sdk"))

    def test_every_sdk_owns_one_distinct_concern(self):
        owns = [e["owns"].casefold() for e in registry.FAMILY.values()]
        self.assertEqual(len(owns), len(set(owns)))


class Assembly(unittest.TestCase):
    def setUp(self):
        self.f = fx.build()
        self.org = self.f.org

    def test_one_keyed_ledger_refuses_a_forged_commitment(self):
        from vega_custody.ledger.ledger import LedgerRefused
        with self.assertRaises(LedgerRefused):
            self.org.ledger.mint({"kind": "WCOMMIT", "device": fx.DEV, "surface": fx.SURF, "action": "run_job", "action_hash": "ab" * 32, "expiry": 9999999999, "nonce_sha256": "cd" * 32})

    def test_a_paid_lane_runs_only_with_a_signed_spend_for_exactly_that_lane_and_query(self):
        from vega_council import deliberation as D
        calls = []
        brains = [D.Brain("a", "f1", lambda p: "x", lambda p, o, s: []), D.Brain("b", "f2", lambda p: "x", lambda p, o, s: []),
                  D.Brain("p", "f3", lambda p: calls.append("paid") or "x", lambda p, o, s: [], cost="paid")]
        council = self.org.council(brains)
        ph = hashlib.sha256(b"q").hexdigest()
        self.assertEqual(council.deliberate("q")["skipped"], ["p"])
        self.org.approvals.present("spend_funds", {"lane": "p", "query_sha256": "00" * 32}, self.f.sign("spend_funds", {"lane": "p", "query_sha256": "00" * 32}))   # signed for another query
        self.assertEqual(council.deliberate("q")["skipped"], ["p"])
        self.org.approvals.present("spend_funds", {"lane": "p", "query_sha256": ph}, self.f.sign("spend_funds", {"lane": "p", "query_sha256": ph}))
        self.assertEqual(council.deliberate("q")["skipped"], [])
        self.assertEqual(calls, ["paid"])
        self.assertEqual(council.deliberate("q")["skipped"], ["p"])                              # single use: the next ask needs a new signature

    def test_the_builder_design_approval_goes_through_the_same_check(self):
        b = self.org.builder()
        h = b.propose_design({"stack": "x"})
        from vega_council.builder import BuilderRefused
        with self.assertRaises(BuilderRefused):
            b.approve(h, self.org.approvals.design_ok)
        self.org.approvals.present("approve_design", {"design_sha256": h}, self.f.sign("approve_design", {"design_sha256": h}))
        b.approve(h, self.org.approvals.design_ok)
        self.assertTrue(b.approved)

    def test_a_signature_from_another_key_is_never_a_yes(self):
        h = "ab" * 32
        from vega_umbrella.organism import OrganismRefused
        with self.assertRaises(OrganismRefused):
            self.org.approvals.present("approve_design", {"design_sha256": h}, self.f.sign_other("approve_design", {"design_sha256": h}))
        self.assertFalse(self.org.approvals.design_ok(h))

    def test_terminal_reasoning_and_trace_lanes_share_the_anchor(self):
        work = self.f.t / "work"
        work.mkdir()
        term = self.org.terminal(str(work))
        (work / "a.txt").write_text("hello")
        self.assertTrue(term.run_agent("cat a.txt")["ok"])
        log = self.org.reasoning_log()
        from vega_reasoning import records
        log.add(records.make("apprentice", "m", "c", "q", "t", "a"))
        a1 = self.org.anchor()
        self.assertEqual(sorted(a1["heads"]), ["reasoning", "terminal"])
        log.add(records.make("apprentice", "m", "c", "q2", "t", "a"))
        a2 = self.org.anchor()
        self.assertNotEqual(a1["root_sha256"], a2["root_sha256"])
        self.assertTrue(self.org.verify_all()["ok"])

    def test_the_feed_watches_every_lane_and_catches_tampering(self):
        work = self.f.t / "work"
        work.mkdir()
        term = self.org.terminal(str(work))
        term.run_agent("pwd")
        self.org.anchor()
        feed = self.org.feed()
        self.assertGreater(len(feed.poll()), 0)
        path = self.org.lane_paths()["terminal"][0]
        pathlib.Path(path).write_bytes(b"{junk")
        self.assertIn("CHAIN_BROKEN", [e["kind"] for e in feed.poll()])
        self.assertFalse(self.org.verify_all()["ok"])

    def test_metacog_trace_and_library_lanes(self):
        L = self.org.metacog_ledger("author")
        L.register("r1", "tests pass")
        L.verify("r1", "ci", True)
        self.assertEqual(L.gate()["status"], "COMPLETE")
        led = self.org.observe_ledger()
        led.observe("s1", "cache", "ab" * 32, {(0, 0): 1.0}, "cd" * 32)
        self.assertIn("trace", self.org.lane_paths())


def family_fixture(tmp, only=None):
    """A fake family folder with every BUILT/PARTIAL SDK complete, so each audit rule can be broken one at a time."""
    lic = b"canonical license text"
    root = pathlib.Path(tmp)
    for name, e in registry.FAMILY.items():
        if e["status"] == "DESIGN":
            continue
        d = root / name
        d.mkdir()
        deps = ", ".join('"%s"' % r for r in e["requires"])
        (d / "pyproject.toml").write_text('[project]\nname = "%s"\ndependencies = [%s]\n' % (name, deps))
        (d / "LICENSE").write_bytes(lic)
        (d / "COMMERCIAL_LICENSE.md").write_text("commercial")
        (d / "REVIEW.json").write_text(json.dumps({"findings": [], "tests": {"ran": True, "ok": True, "tests": 5}}))
        (d / "UNFILED_MATTER.json").write_text(json.dumps({"release_blocked": False, "unfiled_modules": []}))
    return root, hashlib.sha256(lic).hexdigest()


class Audit(unittest.TestCase):
    def test_a_complete_family_is_ready(self):
        root, sha = family_fixture(tempfile.mkdtemp())
        r = audit.audit_family(str(root), sha)
        self.assertEqual(r["verdict"], "READY", r["blocked"])
        self.assertEqual(r["sdks"]["vega-neural-galaxy-sdk"]["verdict"], "NOT_BUILT")

    def test_each_rule_blocks(self):
        root, sha = family_fixture(tempfile.mkdtemp())
        d = root / "vega-trace-sdk"
        (d / "LICENSE").write_bytes(b"another license")
        (root / "vega-metacog-sdk" / "COMMERCIAL_LICENSE.md").unlink()
        (root / "vega-council-sdk" / "REVIEW.json").write_text(json.dumps({"findings": [{"severity": "high"}], "tests": {"ran": True, "ok": True}}))
        (root / "vega-feed-missing").mkdir()
        (root / "vega-governance-feed-sdk" / "pyproject.toml").write_text('[project]\ndependencies = []\n')
        (root / "vega-terminal-sdk" / "REVIEW.json").write_text(json.dumps({"findings": [], "tests": {"ran": True, "ok": False}}))
        r = audit.audit_family(str(root), sha)
        self.assertEqual(r["verdict"], "BLOCKED")
        for n in ("vega-trace-sdk", "vega-metacog-sdk", "vega-council-sdk", "vega-governance-feed-sdk", "vega-terminal-sdk"):
            self.assertIn(n, r["blocked"], n)
        self.assertNotIn("vega-custody-sdk", r["blocked"])

    def test_unfiled_matter_blocks_the_release_but_never_lifts_by_itself(self):
        root, sha = family_fixture(tempfile.mkdtemp())
        (root / "vega-reasoning-sdk" / "UNFILED_MATTER.json").write_text(json.dumps({"release_blocked": True, "unfiled_modules": ["fidelity"]}))
        r = audit.audit_family(str(root), sha)
        self.assertEqual(r["verdict"], "READY")
        self.assertEqual(r["release_blocked"], ["vega-reasoning-sdk"])
        self.assertEqual(audit.audit_family(str(root), sha, public_eligible=["vega-reasoning-sdk"])["release_blocked"], [])


if __name__ == "__main__":
    unittest.main()
