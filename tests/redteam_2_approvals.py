"""RED TEAM 2 - umbrella: the one place that turns a signature into a yes. Replay, swapped parameters, forged and clobbered approvals, races, hostile lane names."""
import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import fixture_umbrella as fx  # noqa: E402
from vega_umbrella import organism as O  # noqa: E402

H = "ab" * 32


class A_Approvals(unittest.TestCase):
    def setUp(self):
        self.f = fx.build()
        self.a = self.f.org.approvals

    def test_an_approval_is_single_use(self):
        self.a.present("approve_design", {"design_sha256": H}, self.f.sign("approve_design", {"design_sha256": H}))
        self.assertTrue(self.a.design_ok(H))
        self.assertFalse(self.a.design_ok(H))

    def test_the_same_signature_offered_twice_works_once(self):
        s = self.f.sign("approve_design", {"design_sha256": H})
        self.a.present("approve_design", {"design_sha256": H}, s)
        self.a.present("approve_design", {"design_sha256": H}, s)
        self.assertTrue(self.a.design_ok(H))
        self.assertFalse(self.a.design_ok(H))

    def test_one_signature_cannot_be_spent_on_another_action_or_parameters(self):
        s = self.f.sign("approve_design", {"design_sha256": H})
        with self.assertRaises(O.OrganismRefused):
            self.a.present("decide_taste", {"token_sha256": H}, s)                                   # offered under the wrong action
        with self.assertRaises(O.OrganismRefused):
            self.a.present("approve_design", {"design_sha256": "cd" * 32}, s)                       # offered under other parameters
        self.assertFalse(self.a.decision_ok(H))
        self.assertFalse(self.a.design_ok("cd" * 32))

    def test_garbage_is_refused_at_the_door_and_cannot_take_a_slot_from_the_real_approval(self):
        for junk in ({}, {"nonce": "x"}, {"signature": "00" * 64, "nonce": "n", "expiry": 9999999999}, {"signature": 5}, self.f.sign_other("approve_design", {"design_sha256": H}),
                     self.f.sign("approve_design", {"design_sha256": "cd" * 32})):
            with self.assertRaises(O.OrganismRefused):
                self.a.present("approve_design", {"design_sha256": H}, junk)
        for _ in range(20):
            with self.assertRaises(O.OrganismRefused):
                self.a.present("approve_design", {"design_sha256": H}, {"junk": 1})
        self.a.present("approve_design", {"design_sha256": H}, self.f.sign("approve_design", {"design_sha256": H}))
        self.assertTrue(self.a.design_ok(H))

    def test_a_used_signature_replayed_into_the_slot_does_not_block_a_fresh_one(self):
        old = self.f.sign("approve_design", {"design_sha256": H})
        self.a.present("approve_design", {"design_sha256": H}, old)
        self.assertTrue(self.a.design_ok(H))
        for _ in range(O.PER_KEY_CAP - 1):
            self.a.present("approve_design", {"design_sha256": H}, old)                                   # replays of the spent one
        self.a.present("approve_design", {"design_sha256": H}, self.f.sign("approve_design", {"design_sha256": H}))
        self.assertTrue(self.a.design_ok(H))

    def test_a_signature_from_another_key_or_an_expired_one_is_no(self):
        with self.assertRaises(O.OrganismRefused):
            self.a.present("approve_design", {"design_sha256": H}, self.f.sign_other("approve_design", {"design_sha256": H}))
        self.assertFalse(self.a.design_ok(H))
        self.a.present("approve_design", {"design_sha256": H}, self.f.sign("approve_design", {"design_sha256": H}, lease=1))
        time.sleep(2.3)
        self.assertFalse(self.a.design_ok(H))                                                          # expired while waiting

    def test_human_only_spend_cannot_be_approved_by_an_ordinary_signature(self):
        params = {"lane": "p", "query_sha256": H}
        with self.assertRaises(O.OrganismRefused):
            self.a.present("spend_funds", params, self.f.sign("approve_design", params))             # signed as a different action
        self.assertFalse(self.a.paid_ok("p", H))

    def test_hostile_arguments_are_no_not_a_crash(self):
        for lane, q in ((None, H), ("p", None), (5, 5), ({"a": 1}, [1]), (object(), "x")):
            self.assertFalse(self.a.paid_ok(lane, q), repr((lane, q)))
        for bad in (("x", {}, None), (5, {}, {}), ("x", [], {}), ("x", {}, "sig"), ("x", {"k": object()}, {})):
            with self.assertRaises(O.OrganismRefused):
                self.a.present(*bad)

    def test_the_pending_pile_is_capped(self):
        with self.assertRaises(O.OrganismRefused):
            for i in range(O.PRESENT_CAP + 10):
                p = {"design_sha256": "%064x" % i}
                self.a.present("approve_design", p, self.f.sign("approve_design", p))

    def test_two_threads_racing_for_one_approval_get_exactly_one_yes(self):
        self.a.present("approve_design", {"design_sha256": H}, self.f.sign("approve_design", {"design_sha256": H}))
        results = []
        ts = [threading.Thread(target=lambda: results.append(self.a.design_ok(H))) for _ in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sum(results), 1)


class B_Organism(unittest.TestCase):
    def setUp(self):
        self.f = fx.build()

    def test_lane_names_are_plain(self):
        for bad in ("", "../x", "a/b", "A", "x" * 40, "a b", "nul\x00", "1a", None):
            with self.assertRaises((O.OrganismRefused, TypeError), msg=repr(bad)):
                self.f.org.lane(bad)

    def test_a_missing_sdk_is_a_clear_error_not_a_crash(self):
        with self.assertRaises(O.OrganismRefused):
            self.f.org._need("vega_not_installed_sdk")

    def test_anchor_records_every_lane_head_and_changes_when_one_changes(self):
        self.f.org.lane("a").record("X", {"id": "1"})
        r1 = self.f.org.anchor()
        self.f.org.lane("a").record("X", {"id": "2"})
        r2 = self.f.org.anchor()
        self.assertNotEqual(r1["root_sha256"], r2["root_sha256"])
        self.assertEqual(r2["heads"]["a"], self.f.org.lane("a").content.head())

    def test_tampering_with_a_lane_shows_in_verify_all(self):
        self.f.org.lane("a").record("X", {"id": "1"})
        import pathlib
        pathlib.Path(self.f.org.lane_paths()["a"][0]).write_bytes(b"{junk")
        r = self.f.org.verify_all()
        self.assertFalse(r["ok"])

    def test_the_ledger_refuses_a_commitment_the_human_did_not_sign_even_through_the_organism(self):
        from vega_custody.ledger.ledger import LedgerRefused
        c = {"kind": "WCOMMIT", "device": fx.DEV, "surface": fx.SURF, "action": "spend_funds", "action_hash": "ab" * 32, "expiry": 9999999999, "nonce_sha256": "cd" * 32}
        with self.assertRaises(LedgerRefused):
            self.f.org.ledger.mint(c)
        self.assertFalse(self.f.org.ledger.verify(c))

    def test_the_organism_holds_no_private_key(self):
        org = self.f.org
        blob = repr(vars(org)) + repr(vars(org.verifier))
        self.assertNotIn("PRIVATE KEY", blob)
        self.assertFalse(hasattr(org, "sign"))
        self.assertFalse(hasattr(org.approvals, "sign"))


if __name__ == "__main__":
    unittest.main()
