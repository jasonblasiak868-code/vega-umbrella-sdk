"""Integration tests: one Organism, one ledger, one approval path, real calls ACROSS kits. Each test crosses at least one kit boundary, because a function that passes its own unit
tests but is never called by the code that should call it (the prompt layers in the harness pipeline were exactly that) is invisible to unit tests."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_umbrella as fx  # noqa: E402
from vega_umbrella import organism, registry  # noqa: E402

VERIFY = lambda ctx: ctx.get("answer") == 42


class HarnessThroughTheOrganism(unittest.TestCase):
    def setUp(self):
        self.f = fx.build()
        self.org = self.f.org

    def steps(self):
        from vega_harness import conductor as cd
        return [cd.Step("spend", lambda ctx: {"answer": 42}, verbs=["spend_funds"])]

    def test_a_human_only_step_runs_once_on_a_commitment_from_the_one_ledger(self):
        c = self.org.conductor()
        steps = self.steps()
        self.assertTrue(c.run("t0", {}, steps, VERIFY)["status"].startswith("refused"))
        params = {"why": "test"}
        commitment = self.org.commit_for("conductor_step:spend", params, self.f.sign("conductor_step:spend", params))
        self.assertEqual(c.run("t1", {}, steps, VERIFY, commitment=commitment)["status"], "success")
        self.assertTrue(c.run("t2", {}, steps, VERIFY, commitment=commitment)["status"].startswith("refused"))          # one signature, one use

    def test_a_commitment_that_was_never_minted_is_refused_by_the_conductor(self):
        c = self.org.conductor()
        forged = {"kind": "WCOMMIT", "device": fx.DEV, "surface": fx.SURF, "action": "conductor_step:spend", "action_hash": "ab" * 32, "expiry": 9999999999, "nonce_sha256": "cd" * 32}
        self.assertTrue(c.run("t", {}, self.steps(), VERIFY, commitment=forged)["status"].startswith("refused"))

    def test_the_pipeline_asks_the_arsenal_and_records_the_prompt_layers(self):
        ars = self.org.arsenal()
        ars.add("symbol", "chain_verify", "Verify a hash chain end to end and report the first broken link", path="custody/dag.py:Chain.verify", score=0.95)
        ars.add("tool", "secret_scan", "Scan a staged tree for credential shaped strings before a push", score=0.8)
        out = self.org.plan({"goal": "verify that my hash chain is intact"}, deps={"arsenal": ars.as_dependency()})
        self.assertEqual(out["run"]["status"], "success")
        bp = out["blueprint"]
        self.assertEqual(bp["arsenal"]["status"], "BUILT")
        self.assertEqual(bp["arsenal"]["hits"][0]["name"], "chain_verify")
        self.assertEqual(bp["arsenal"]["index_hash"], ars.index_hash())
        self.assertEqual([l["name"] for l in bp["cache_prefix"]["layers"]], ["policy", "goal", "anchors"])             # prompt_layers is called by the pipeline
        self.assertNotIn("arsenal", bp["unbuilt"])

    def test_stage_18_runs_a_frozen_path_only_on_two_commitments_from_the_one_ledger(self):
        from vega_harness import predicted_path as pp
        spec = {"goal": "g", "steps": [{"name": "s", "do": "one", "expect": {"equals": 1}, "read_only": True}]}
        reg = {"actions": {"one": lambda st: 1}}
        deps = {"predict_path": lambda ctx: (spec, reg)}
        step_action = "conductor_step:s18_execute_under_commitment"
        c1 = self.org.commit_for(step_action, {"s": 1}, self.f.sign(step_action, {"s": 1}))
        spec_action = "execute:" + pp.spec_hash(spec)
        c2 = self.org.commit_for(spec_action, {"spec": 1}, self.f.sign(spec_action, {"spec": 1}))
        forged = dict(c2, nonce_sha256="ee" * 32)
        refused = self.org.plan({"goal": "run the frozen path"}, deps=deps, execute=True, commitment=c1, spec_commitment=forged)
        self.assertFalse(refused["execution"] and refused["execution"].get("status") == "completed")
        c1b = self.org.commit_for(step_action, {"s": 2}, self.f.sign(step_action, {"s": 2}))
        ok = self.org.plan({"goal": "run the frozen path"}, deps=deps, execute=True, commitment=c1b, spec_commitment=c2)
        self.assertEqual(ok["execution"]["status"], "completed")

    def test_the_policy_layer_is_identical_for_two_requests(self):
        a = self.org.plan({"goal": "first goal here"})["blueprint"]["cache_prefix"]["layers"][0]["prefix_hash"]
        b = self.org.plan({"goal": "a completely different goal"})["blueprint"]["cache_prefix"]["layers"][0]["prefix_hash"]
        self.assertEqual(a, b)

    def test_an_empty_arsenal_leaves_the_stage_unbuilt(self):
        out = self.org.plan({"goal": "anything at all"}, deps={"arsenal": self.org.arsenal().as_dependency()})
        self.assertIn("arsenal", out["blueprint"]["unbuilt"])


class KronosThroughTheOrganism(unittest.TestCase):
    def setUp(self):
        self.f = fx.build()
        self.org = self.f.org

    def test_a_job_runs_on_a_commitment_for_exactly_that_job_and_only_once(self):
        from vega_custody.capsule import capsule as cap
        from vega_twogate.kronos import contain
        k, hs = self.org.containment()
        req = cap.make("payload", {"source": "user"})
        argv = [sys.executable, "-I", "-c", "print('hello')"]
        params = contain.job_params("job1", argv, req)
        commitment = self.org.commit_for("run_job", params, self.f.sign("run_job", params))
        with self.assertRaises(contain.ContainmentRefused) as cm:
            k.run("job2", argv, req, commitment, timeout=20)                                   # a signature for job1 cannot start job2, even though it was never used
        self.assertIn("bind", str(cm.exception))
        out = k.run("job1", argv, req, commitment, timeout=20)
        self.assertEqual(cap.data_of(out).strip(), b"hello")
        with self.assertRaises(contain.ContainmentRefused):
            k.run("job1", argv, req, commitment, timeout=20)                                   # and job1 itself only once

    def test_the_hard_stop_lifts_only_with_a_human_signature_through_the_organism(self):
        from vega_custody.capsule import capsule as cap
        from vega_twogate.kronos import contain
        k, hs = self.org.containment()
        hs.engage("test")
        req = cap.make("payload", {"source": "user"})
        argv = [sys.executable, "-I", "-c", "print(1)"]
        params = contain.job_params("j", argv, req)
        commitment = self.org.commit_for("run_job", params, self.f.sign("run_job", params))
        with self.assertRaises(contain.HardStopEngaged):
            k.run("j", argv, req, commitment, timeout=20)
        with self.assertRaises(contain.ContainmentRefused):
            self.org.lift_hard_stop(hs, {"why": "x"}, self.f.sign_other("restore_after_hard_stop", {"why": "x"}))            # the wrong key
        self.org.lift_hard_stop(hs, {"why": "x"}, self.f.sign("restore_after_hard_stop", {"why": "x"}))
        self.assertFalse(hs.engaged())


class PareahThroughTheOrganism(unittest.TestCase):
    def test_a_revoked_pre_stops_a_connection_made_through_the_organism(self):
        from vega_custody.capsule import capsule as cap
        from vega_pareah.adapter import adapter_card, pareah
        from vega_pareah.cards import pre as pre_mod
        f = fx.build()
        deck = f.org.pre_deck()
        pa = f.org.pareah(pre_deck=deck)
        card = adapter_card.mint_adapter_card("echo", "tool", ["echo"], "ab" * 32, "permissive", "https://example/echo")
        pre = pre_mod.mint_pre("agent", ["connect_adapter", "echo"], ["echo", "/work/"], 300)
        deck.add(pre)
        a, b = pareah.End("agent-side"), pareah.End("adapter-side")
        params = {"union": pareah.union_hash(card, a, b, pre), "adapter": card["card_hash"], "pre": pre["card_hash"]}
        conn = pa.connect(card, pre, a, b, f.sign(pareah.UNION_ACTION, params), lambda p: "echo:%s" % p)
        req = lambda: cap.make("hi", {"action": "echo", "resource": "echo"})
        self.assertEqual(cap.data_of(conn.call(req())), "echo:hi")
        deck.revoke(pre["card_hash"])
        with self.assertRaises(pareah.PareahRefused):
            conn.call(req())


class LanesAreOneRecord(unittest.TestCase):
    def test_identity_and_journal_write_to_their_own_lanes_and_the_anchor_covers_them(self):
        import secrets
        f = fx.build()
        org = f.org
        idn = org.identity(secrets.token_bytes(32), b"pepper-pepper-pepper", secrets.token_bytes(32), scrypt_n=2 ** 10)
        idn.enrol("alex", "purple river lantern 42 quietly")
        self.assertTrue(idn.login("alex").password("purple river lantern 42 quietly"))
        j = org.journal(str(f.t / "journal.jsonl"))
        j.add("owner", "a first entry")
        anchor = org.anchor()
        self.assertTrue({"identity", "journal"} <= set(anchor["heads"]))
        self.assertTrue(org.verify_all()["ok"])
        before = anchor["root_sha256"]
        j.add("owner", "a second entry")
        self.assertNotEqual(org.anchor()["root_sha256"], before)

    def test_the_governance_feed_sees_the_new_lanes(self):
        import secrets
        f = fx.build()
        idn = f.org.identity(secrets.token_bytes(32), b"pepper-pepper-pepper", secrets.token_bytes(32), scrypt_n=2 ** 10)
        idn.enrol("alex", "purple river lantern 42 quietly")
        events = f.org.feed().poll()
        self.assertTrue(any(e["source"] == "identity" and e["kind"] == "ID_ENROLLED" for e in events))


class TheRegistryMatchesTheWiring(unittest.TestCase):
    def test_every_kit_the_organism_imports_is_a_declared_dependency_of_the_umbrella(self):
        pkg_to_sdk = {e["package"]: n for n, e in registry.FAMILY.items()}
        need = set(registry.FAMILY["vega-umbrella-sdk"]["requires"])
        for key in organism._IMPORTERS:
            top = key.split(".")[0]
            self.assertIn(top, pkg_to_sdk, key)
            self.assertIn(pkg_to_sdk[top], need, "%s is imported by the organism but not declared" % key)

    def test_the_registry_is_still_sound(self):
        self.assertTrue(registry.check_registry())


if __name__ == "__main__":
    unittest.main()
