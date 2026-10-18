"""Tests for the feedback draft builder, with the attacks a hostile or careless text could try."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from vega_umbrella import feedback as F  # noqa: E402

CFG = F.FeedbackConfig("owner@example.com")


class Basics(unittest.TestCase):
    def test_subject_names_the_system_and_the_draft_is_not_sent_by_us(self):
        m = F.build_message(CFG, "vega-os/galaxy", "The pointer is better now.", version="0.1.0")
        self.assertEqual(m["subject"], "Review: vega-os/galaxy")
        self.assertFalse(m["sends_automatically"])
        self.assertEqual(m["attachments"], [])
        p = F.parse_mailto(m["mailto"])
        self.assertEqual((p["to"], p["subject"], p["keys"]), ("owner@example.com", "Review: vega-os/galaxy", ["body", "subject"]))
        self.assertIn("-- Sent from vega-os/galaxy 0.1.0", p["body"])

    def test_every_sdk_name_in_the_registry_is_accepted(self):
        from vega_umbrella import registry
        for n in registry.FAMILY:
            self.assertEqual(F.build_message(CFG, n, "ok")["subject"], "Review: %s" % n)

    def test_the_owner_configuration_is_the_address_the_owner_gave(self):
        cfg = F.FeedbackConfig.owner()
        self.assertEqual(cfg.recipient, "jasonblasiak.ai.mail@gmail.com")
        m = F.build_message(cfg, "vega-os", "hello")
        self.assertEqual(F.parse_mailto(m["mailto"])["to"], "jasonblasiak.ai.mail@gmail.com")

    def test_feedback_kind(self):
        self.assertEqual(F.build_message(CFG, "vega-os", "ok", kind="feedback")["subject"], "Feedback: vega-os")

    def test_unicode_survives_the_round_trip(self):
        text = "Très bien — 日本語 and emoji-free text. a&b=c?d#e%20f"
        p = F.parse_mailto(F.build_message(CFG, "vega-os", text)["mailto"])
        self.assertIn(text, p["body"])


class Attacks(unittest.TestCase):
    def test_no_address_means_no_draft(self):
        for cfg in (F.FeedbackConfig(), None, "owner@example.com"):
            with self.assertRaises(F.FeedbackRefused):
                F.build_message(cfg, "vega-os", "x")

    def test_bad_addresses_are_refused(self):
        for bad in ("", "a", "a@b", "a@b@c.com", "a b@c.com", "a@c.com,b@c.com", "a@c.com;b@c.com", "a@c.com\r\nBcc: x@y.com", "a@c.com?bcc=x@y.com", "<a@c.com>", "a@c..com", "a@c.com" + chr(10), 5):
            with self.assertRaises(F.FeedbackRefused, msg=repr(bad)):
                F.FeedbackConfig(bad)

    def test_unknown_or_tricky_system_names_are_refused(self):
        for bad in ("", "vega-os\r\nBcc: x@y.com", "vega-os; rm", "random-product", "vega-nothing-sdk", "vega-os/../x", "vega-os/", "VEGA-OS", "vega-os/a b", None, 5, "vega-os/" + "x" * 80, "vega-os" + chr(10)):
            with self.assertRaises(F.FeedbackRefused, msg=repr(bad)):
                F.build_message(CFG, bad, "text")

    def test_header_injection_through_the_text_cannot_add_recipients(self):
        text = "nice\r\nBcc: attacker@evil.com\r\n\r\nmore&bcc=attacker@evil.com&cc=x@y.com"
        m = F.build_message(CFG, "vega-os", text)
        p = F.parse_mailto(m["mailto"])
        self.assertEqual(p["keys"], ["body", "subject"])
        self.assertEqual(p["to"], "owner@example.com")
        self.assertNotIn("\r", m["mailto"])
        self.assertNotIn("%0D", m["mailto"])

    def test_invisible_and_override_characters_are_removed(self):
        m = F.build_message(CFG, "vega-os", "hel\u202elo\u200b w\x00orld\x1b[2J")
        self.assertEqual(F.parse_mailto(m["mailto"])["body"].split("\n")[0], "hello world[2J")

    def test_text_that_looks_like_a_key_is_refused(self):
        for key in ("sk-" + "a1B2c3D4" * 4, "ghp_" + "a" * 36, "password = hunter2hunter2hunter2hunter2", "nvapi-" + "A1b2C3d4E5" * 3, "-----BEGIN " + "PRIVATE KEY-----"):
            with self.assertRaises(F.FeedbackRefused, msg=key[:20]):
                F.build_message(CFG, "vega-os", "my key is " + key)

    def test_empty_blank_and_oversized_text_and_wrong_types(self):
        for bad in ("", "   ", "\n\t", "\u200b\u200b", "x" * (F.MAX_TEXT + 1), None, 5, ["a"], b"bytes"):
            with self.assertRaises(F.FeedbackRefused, msg=repr(bad)[:30]):
                F.build_message(CFG, "vega-os", bad)

    def test_a_long_message_gets_a_short_link_and_keeps_the_full_text_for_copying(self):
        text = "word " * 700
        m = F.build_message(CFG, "vega-os", text)
        self.assertTrue(m["truncated"])
        self.assertLessEqual(len(m["mailto"]), F.MAX_LINK)
        self.assertIn(text.strip(), m["body"])
        self.assertEqual(F.parse_mailto(m["mailto"])["keys"], ["body", "subject"])

    def test_bad_versions_and_kinds(self):
        for v in ("1 0", "x\r\n", "v" * 40, 5, ""):
            with self.assertRaises(F.FeedbackRefused, msg=repr(v)):
                F.build_message(CFG, "vega-os", "x", version=v)
        for k in ("complaint", "", None, "REVIEW"):
            with self.assertRaises(F.FeedbackRefused):
                F.build_message(CFG, "vega-os", "x", kind=k)

    def test_the_message_never_carries_a_path_or_user_name(self):
        m = F.build_message(CFG, "vega-os", "hello", version="0.1.0")
        for needle in ("C:\\", "jjb20", "Users", os.environ.get("USERNAME", "zzzz-none")):
            self.assertNotIn(needle, m["body"])

    def test_parse_mailto_refuses_other_links(self):
        for bad in ("http://x", "javascript:alert(1)", "mailto:a@b.co?subject=x&subject", ""):
            with self.assertRaises((F.FeedbackRefused, ValueError)):
                F.parse_mailto(bad)


if __name__ == "__main__":
    unittest.main()
