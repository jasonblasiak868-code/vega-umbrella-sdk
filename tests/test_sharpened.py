"""Tests added after the mutation check found umbrella fixes no earlier test noticed."""
import copy
import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import fixture_umbrella as fx  # noqa: E402
from vega_umbrella import organism as O  # noqa: E402
from vega_umbrella import registry  # noqa: E402

H = "ab" * 32


class Sharpened(unittest.TestCase):
    def test_a_bad_sdk_name_is_refused_even_when_everything_else_about_it_is_fine(self):
        f = copy.deepcopy(registry.FAMILY)
        f["not-a-valid-name"] = dict(package="vega_other", layer=14, owns="a brand new concern", requires=["vega-custody-sdk"], status="DESIGN")
        with self.assertRaises(registry.RegistryRefused):
            registry.check_registry(f)

    def test_only_a_few_approvals_can_wait_for_one_action(self):
        f = fx.build()
        a = f.org.approvals
        for _ in range(O.PER_KEY_CAP):
            a.present("approve_design", {"design_sha256": H}, f.sign("approve_design", {"design_sha256": H}))
        with self.assertRaises(O.OrganismRefused):
            a.present("approve_design", {"design_sha256": H}, f.sign("approve_design", {"design_sha256": H}))

    def test_the_router_built_by_the_organism_asks_the_one_approval_check_before_a_paid_lane(self):
        from vega_reasoning import morna
        f = fx.build()
        calls = []
        lanes = [morna.Lane("paid_ref", lambda q: calls.append(q) or "answer", "paid", "reference", ["code"])]
        router = f.org.router(lanes, lambda: [])
        self.assertFalse(router.route("code", "question")["ok"])
        self.assertEqual(calls, [])
        qh = hashlib.sha256(b"question").hexdigest()
        params = {"lane": "paid_ref", "query_sha256": qh}
        f.org.approvals.present("spend_funds", params, f.sign("spend_funds", params))
        out = router.route("code", "question")
        self.assertTrue(out["ok"])
        self.assertEqual(calls, ["question"])

    def test_a_missing_family_folder_blocks_with_its_own_reason(self):
        import tempfile
        from vega_umbrella import audit
        r = audit.audit_family(tempfile.mkdtemp(), "00" * 32)
        self.assertEqual(r["sdks"]["vega-custody-sdk"]["reasons"], ["folder is missing"])


if __name__ == "__main__":
    unittest.main()
