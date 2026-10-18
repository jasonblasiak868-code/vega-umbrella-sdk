"""RED TEAM 1 - umbrella: a registry that lets two SDKs fight over a concern, and an audit that can be fooled by odd files."""
import copy
import hashlib
import json
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from test_umbrella import family_fixture  # noqa: E402
from vega_umbrella import audit, registry  # noqa: E402


def fam():
    return copy.deepcopy(registry.FAMILY)


class A_Registry(unittest.TestCase):
    def refused(self, mutate):
        f = fam()
        mutate(f)
        with self.assertRaises(registry.RegistryRefused):
            registry.check_registry(f)

    def test_two_owners_of_one_concern_are_refused_whatever_the_case_or_spacing(self):
        self.refused(lambda f: f["vega-trace-sdk"].update(owns=f["vega-metacog-sdk"]["owns"].upper()))
        self.refused(lambda f: f["vega-trace-sdk"].update(owns="  " + f["vega-metacog-sdk"]["owns"] + "  "[:0]))

    def test_a_dependency_must_point_to_a_lower_layer(self):
        self.refused(lambda f: f["vega-custody-sdk"].update(requires=["vega-trace-sdk"]))
        self.refused(lambda f: f["vega-trace-sdk"].update(requires=["vega-reasoning-sdk"]))          # layer 10 on layer 11
        self.refused(lambda f: f["vega-trace-sdk"].update(requires=["vega-trace-sdk"]))              # itself

    def test_unknown_dependencies_names_statuses_layers_and_packages_are_refused(self):
        self.refused(lambda f: f["vega-trace-sdk"].update(requires=["vega-nonexistent-sdk"]))
        self.refused(lambda f: f.update({"not-a-name": dict(f["vega-trace-sdk"])}))
        self.refused(lambda f: f.update({"vega-bad-sdk": dict(f["vega-trace-sdk"], owns="something else", package="vega_bad", status="DONE")}))
        self.refused(lambda f: f.update({"vega-bad-sdk": dict(f["vega-trace-sdk"], owns="something else", package="vega_bad", layer=99)}))
        self.refused(lambda f: f.update({"vega-bad-sdk": dict(f["vega-trace-sdk"], owns="something else", package="vega_bad", layer=True)}))
        self.refused(lambda f: f.update({"vega-bad-sdk": dict(f["vega-trace-sdk"], owns="something else", package="vega_trace")}))      # same package name
        self.refused(lambda f: f["vega-trace-sdk"].update(owns=""))
        self.refused(lambda f: f["vega-trace-sdk"].update(owns=None))

    def test_a_new_sdk_that_claims_a_new_concern_is_accepted(self):
        f = fam()
        f["vega-new-sdk"] = dict(package="vega_new", layer=14, owns="a concern nobody owns", requires=["vega-custody-sdk"], status="DESIGN")
        self.assertTrue(registry.check_registry(f))

    def test_build_order_puts_dependencies_first_and_refuses_a_broken_registry(self):
        order = registry.build_order()
        pos = {n: i for i, n in enumerate(order)}
        for n, e in registry.FAMILY.items():
            for d in e["requires"]:
                self.assertLess(pos[d], pos[n])
        f = fam()
        f["vega-custody-sdk"]["requires"] = ["vega-council-sdk"]
        with self.assertRaises(registry.RegistryRefused):
            registry.build_order(f)


class B_Audit(unittest.TestCase):
    def setUp(self):
        self.root, self.sha = family_fixture(tempfile.mkdtemp())

    def verdict(self):
        return audit.audit_family(str(self.root), self.sha)

    def test_wrong_shaped_files_block_and_never_crash_or_pass(self):
        d = self.root / "vega-trace-sdk"
        for fname, body in (("REVIEW.json", "[]"), ("REVIEW.json", "null"), ("REVIEW.json", "not json"), ("REVIEW.json", json.dumps({"findings": "none", "tests": {"ran": True, "ok": True}})),
                            ("REVIEW.json", json.dumps({"findings": [1, 2], "tests": {"ran": True, "ok": True}})), ("REVIEW.json", json.dumps({"findings": [], "tests": {"ran": "yes", "ok": 1}})),
                            ("REVIEW.json", json.dumps({"findings": [], "tests": []})), ("UNFILED_MATTER.json", "[]"), ("UNFILED_MATTER.json", json.dumps({"unfiled_modules": "all"})),
                            ("UNFILED_MATTER.json", "{broken"), ("pyproject.toml", "\x00\x01 garbage")):
            good = (d / fname).read_text(encoding="utf-8")
            (d / fname).write_text(body, encoding="utf-8")
            r = self.verdict()
            self.assertIn("vega-trace-sdk", r["blocked"], "%s <- %r" % (fname, body[:30]))
            (d / fname).write_text(good, encoding="utf-8")
        self.assertEqual(self.verdict()["verdict"], "READY")

    def test_license_tricks(self):
        d = self.root / "vega-trace-sdk"
        (d / "LICENSE").write_bytes(b"canonical license text\n")                                   # one byte different
        self.assertIn("vega-trace-sdk", self.verdict()["blocked"])
        (d / "LICENSE").unlink()
        (d / "LICENSE").mkdir()                                                                       # a folder where the file should be
        self.assertIn("vega-trace-sdk", self.verdict()["blocked"])

    def test_a_missing_family_root_or_empty_root_blocks(self):
        r = audit.audit_family(str(self.root / "nope"), self.sha)
        self.assertEqual(r["verdict"], "BLOCKED")
        r = audit.audit_family(tempfile.mkdtemp(), self.sha)
        self.assertEqual(r["verdict"], "BLOCKED")

    def test_a_dependency_missing_from_the_pyproject_blocks(self):
        d = self.root / "vega-council-sdk"
        (d / "pyproject.toml").write_text('[project]\nname = "x"\ndependencies = ["vega-custody-sdk"]\n')
        r = self.verdict()
        self.assertIn("vega-council-sdk", r["blocked"])
        self.assertTrue(any("vega-harness-sdk" in x for x in r["sdks"]["vega-council-sdk"]["reasons"]))

    def test_a_huge_review_file_is_refused_not_loaded(self):
        d = self.root / "vega-trace-sdk"
        with open(d / "REVIEW.json", "wb") as fh:
            fh.truncate(audit.CAP + 10)
        self.assertIn("vega-trace-sdk", self.verdict()["blocked"])

    def test_the_audit_never_writes_to_the_family(self):
        before = sorted(str(p) for p in self.root.rglob("*"))
        self.verdict()
        self.assertEqual(before, sorted(str(p) for p in self.root.rglob("*")))

    def test_design_only_sdks_are_not_audited_and_do_not_block(self):
        r = self.verdict()
        self.assertEqual(r["sdks"]["vega-neural-galaxy-sdk"]["verdict"], "NOT_BUILT")
        self.assertNotIn("vega-neural-galaxy-sdk", r["blocked"])

    def test_a_clean_review_does_not_lift_the_release_block(self):
        d = self.root / "vega-trace-sdk"
        (d / "UNFILED_MATTER.json").write_text(json.dumps({"release_blocked": True, "unfiled_modules": []}))
        self.assertEqual(self.verdict()["release_blocked"], ["vega-trace-sdk"])
        self.assertEqual(audit.audit_family(str(self.root), self.sha, public_eligible=["some-other-sdk"])["release_blocked"], ["vega-trace-sdk"])


if __name__ == "__main__":
    unittest.main()
