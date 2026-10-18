"""feedback.py - the feedback icon's engine: turns what a user typed into an email draft addressed to the owner, with the subject saying which system it came from.

WHY A DRAFT AND NOT A SILENT SEND: a program that sends mail by itself must carry a mail account's password, and any password shipped inside software can be pulled out of it. So this module builds the message and a `mailto:` link; the user's own mail program opens with the draft filled in, the user reads exactly what will go, and presses Send themselves. Nothing leaves without the user's own action, nothing is attached, and no secret exists in the software. (A forwarding service run by the owner is a possible later step; it needs hosting, spam limits and a privacy notice, and is not part of this module.)

  FeedbackConfig(recipient)       the owner's address; refused until it is set and well formed (one plain address; no lists, no line breaks)
  build_message(cfg, system, text, kind, version)
       system   a known SDK name from the registry, or 'vega-os', or 'vega-os/<panel>'
       subject  'Review: <system>' (or 'Feedback: <system>' for kind 'feedback'): the system it was routed from
       body     what the user wrote, plus one footer line naming the system and version; never a path, user name, machine name, log or record
       refuses  empty or over-long text, control characters used for tricks (they are stripped), text that looks like it holds a key or token (the user is told to remove it)
  The mailto link is length-limited (mail programs cut long links): a long message gets a shortened link plus the full text for 'Copy full text', and `truncated` says so."""
import re
import unicodedata

from vega_custody.dag.dag import contains_credential
from vega_umbrella import registry

MAX_TEXT = 4000
MAX_LINK = 1800
KINDS = {"review": "Review", "feedback": "Feedback"}
_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9\-]{1,63}(\.[A-Za-z0-9\-]{1,63}){1,5}$")
_SYSTEM = re.compile(r"^(vega-os(/[a-z0-9][a-z0-9-]{0,40})?|vega-[a-z0-9-]+-sdk(/[a-z0-9][a-z0-9-]{0,40})?)$")
_VERSION = re.compile(r"^[0-9A-Za-z.+\-]{1,32}$")


_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


def _pct(text):
    """Percent-encode every byte of the UTF-8 text except the unreserved characters (so '&', '=', '?', '#', '%', spaces and line breaks can never act as link syntax)."""
    out = []
    for b in text.encode("utf-8"):
        c = chr(b)
        out.append(c if b < 128 and c in _UNRESERVED else "%%%02X" % b)
    return "".join(out)


def _unpct(text):
    raw = bytearray()
    i = 0
    while i < len(text):
        if text[i] == "%":
            if not re.fullmatch(r"[0-9A-Fa-f]{2}", text[i + 1:i + 3]):
                raise FeedbackRefused("bad percent escape in link")
            raw.append(int(text[i + 1:i + 3], 16))
            i += 3
        else:
            raw += text[i].encode("utf-8")
            i += 1
    return raw.decode("utf-8")


class FeedbackRefused(ValueError):
    pass


OWNER_FEEDBACK_ADDRESS = "jasonblasiak.ai.mail@gmail.com"      # given by the owner in chat on 2026-10-17 (first dictation, 'jasonblazak', was corrected by the owner to this spelling)


class FeedbackConfig:
    @classmethod
    def owner(cls):
        """The owner's feedback address. NOTE: it sits in the source, so anyone who reads a public copy can see it; a forwarding alias would keep the real mailbox out of public view."""
        return cls(OWNER_FEEDBACK_ADDRESS)

    def __init__(self, recipient=None):
        self.recipient = None
        if recipient is not None:
            if not isinstance(recipient, str) or not _EMAIL.fullmatch(recipient):
                raise FeedbackRefused("the feedback address must be one plain email address")
            self.recipient = recipient


def _clean_text(t):
    """Keep ordinary characters, tabs and line breaks; drop other control, format and bidirectional-override characters; normalise line breaks."""
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    out = []
    for c in t:
        cat = unicodedata.category(c)
        if c in "\n\t" or (cat not in ("Cc", "Cf", "Zl", "Zp") and c != "\x7f"):
            out.append(c)
    return "".join(out).strip()


def known_system(system):
    if not isinstance(system, str) or not _SYSTEM.fullmatch(system):
        return False
    base = system.split("/")[0]
    return base == "vega-os" or base in registry.FAMILY


def build_message(cfg, system, text, kind="review", version=None):
    if not isinstance(cfg, FeedbackConfig) or cfg.recipient is None:
        raise FeedbackRefused("no feedback address is set: the owner must configure one before feedback can be drafted")
    if not known_system(system):
        raise FeedbackRefused("system must be 'vega-os', 'vega-os/<panel>' or a known SDK name")
    if kind not in KINDS:
        raise FeedbackRefused("kind is one of %s" % sorted(KINDS))
    if version is not None and (not isinstance(version, str) or not _VERSION.fullmatch(version)):
        raise FeedbackRefused("version is a short plain version string")
    if not isinstance(text, str):
        raise FeedbackRefused("feedback is text")
    body_text = _clean_text(text)
    if not body_text:
        raise FeedbackRefused("write something first")
    if len(body_text) > MAX_TEXT:
        raise FeedbackRefused("feedback is limited to %d characters" % MAX_TEXT)
    if contains_credential(body_text):
        raise FeedbackRefused("this looks like it contains a key, token or password: please remove it before sending")
    subject = "%s: %s" % (KINDS[kind], system)
    footer = "-- Sent from %s%s" % (system, (" " + version) if version else "")
    full_body = body_text + "\n\n" + footer

    def link(body):
        return "mailto:%s?subject=%s&body=%s" % (cfg.recipient, _pct(subject), _pct(body))
    url, truncated = link(full_body), False
    if len(url) > MAX_LINK:
        truncated = True
        keep = len(body_text)
        while keep > 0:
            note = body_text[:keep].rstrip() + "\n[shortened: use 'Copy full text']\n\n" + footer
            url = link(note)
            if len(url) <= MAX_LINK:
                break
            keep -= max(20, keep // 10)
        else:
            url = link(footer)
    return {"to": cfg.recipient, "subject": subject, "body": full_body, "mailto": url, "truncated": truncated, "attachments": [], "sends_automatically": False}


def parse_mailto(url):
    """For the preview screen and for tests: the exact recipient, subject and body a mailto link will produce. A repeated or unknown key is refused."""
    if not isinstance(url, str) or not url.startswith("mailto:"):
        raise FeedbackRefused("not a mailto link")
    rest = url[len("mailto:"):]
    path, _, query = rest.partition("?")
    if not query:
        raise FeedbackRefused("a feedback link carries a subject and a body")
    parts = {}
    for item in query.split("&"):
        k, eq, v = item.partition("=")
        if not eq or k in parts or k not in ("subject", "body"):
            raise FeedbackRefused("a feedback link has one subject and one body and nothing else")
        parts[k] = _unpct(v)
    return {"to": _unpct(path), "keys": sorted(parts), "subject": parts.get("subject", ""), "body": parts.get("body", "")}
