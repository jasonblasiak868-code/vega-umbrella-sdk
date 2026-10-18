"""audit.py - the pre-deploy gate: is the family fit to be put together and run?

audit_family(root, canonical_license_sha256) reads the SDK folders under root (it never writes to them) and reports, per SDK and overall, READY or BLOCKED with the reasons:
  - the registry is sound (one owner per concern, dependencies point down, no cycle)
  - every BUILT or PARTIAL SDK in the registry exists on disk, with a pyproject whose dependencies cover what the registry says it requires
  - LICENSE is present and is the canonical file (by hash); COMMERCIAL_LICENSE.md is present
  - REVIEW.json exists and has no high or medium finding
  - tests were run in the review and passed
  - UNFILED_MATTER.json is read: any module tied to unfiled matter keeps the SDK release-blocked until the owner lists it in PUBLIC_ELIGIBLE.json (the audit REPORTS this; it never lifts it)
It does not run anything and does not decide to publish: BLOCKED is a stop, READY only means nothing this audit looks at is in the way."""
import hashlib
import json
import os
import re

from vega_custody import safepaths as sp
from vega_umbrella import registry

CAP = 4 * 1024 * 1024


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _json(path):
    try:
        d = json.loads(sp.read_capped(path, CAP).decode("utf-8"))
    except (OSError, ValueError, sp.PathRefused):
        return None
    return d if isinstance(d, dict) else None                          # a file of the wrong shape is a missing file, never a crash and never a pass


def _deps(pyproject):
    try:
        text = sp.read_capped(pyproject, CAP).decode("utf-8")
    except (OSError, sp.PathRefused):
        return None
    m = re.search(r"dependencies = \[(.*?)\]", text, re.S)
    return {re.split(r"[<>=!~\[ ]", d.strip().strip('"'))[0] for d in (m.group(1).split(",") if m else []) if d.strip()}


def audit_family(root, canonical_license_sha256, public_eligible=None):
    root = os.path.realpath(root)
    out = {"sdks": {}, "problems": []}
    try:
        registry.check_registry()
    except registry.RegistryRefused as exc:
        out["problems"].append("registry: %s" % exc)
    eligible = set(public_eligible or [])
    for name, e in registry.FAMILY.items():
        if e["status"] == "DESIGN":
            out["sdks"][name] = {"verdict": "NOT_BUILT", "reasons": ["design only: nothing to audit"]}
            continue
        d = os.path.join(root, name)
        reasons = []
        if not os.path.isdir(d):
            out["sdks"][name] = {"verdict": "BLOCKED", "reasons": ["folder is missing"]}
            continue
        deps = _deps(os.path.join(d, "pyproject.toml"))
        if deps is None:
            reasons.append("no readable pyproject.toml")
        else:
            missing = sorted(set(e["requires"]) - deps)
            if missing:
                reasons.append("pyproject does not declare: %s" % ", ".join(missing))
        lic = os.path.join(d, "LICENSE")
        if not os.path.isfile(lic):
            reasons.append("LICENSE is missing")
        elif _sha(lic) != canonical_license_sha256:
            reasons.append("LICENSE is not the canonical file")
        if not os.path.isfile(os.path.join(d, "COMMERCIAL_LICENSE.md")):
            reasons.append("COMMERCIAL_LICENSE.md is missing")
        rv = _json(os.path.join(d, "REVIEW.json"))
        if rv is None:
            reasons.append("REVIEW.json is missing or unreadable")
        else:
            fl = rv.get("findings")
            if not isinstance(fl, list) or any(not isinstance(f, dict) for f in fl):
                reasons.append("REVIEW.json findings are not a list of findings")
            else:
                sev = [f.get("severity") for f in fl]
                if "high" in sev or "medium" in sev:
                    reasons.append("review has %d high and %d medium findings" % (sev.count("high"), sev.count("medium")))
            t = rv.get("tests")
            if not (isinstance(t, dict) and t.get("ran") is True and t.get("ok") is True):
                reasons.append("the review's test run did not pass")
        um = _json(os.path.join(d, "UNFILED_MATTER.json"))
        note = None
        if um is None:
            reasons.append("UNFILED_MATTER.json is missing")
        elif not isinstance(um.get("unfiled_modules"), list):
            reasons.append("UNFILED_MATTER.json has no unfiled_modules list")
        elif (um["unfiled_modules"] or um.get("release_blocked") is True) and name not in eligible:
            note = "release-blocked: %d module(s) tied to unfiled matter (or the file says blocked) and the SDK is not in PUBLIC_ELIGIBLE" % len(um["unfiled_modules"])
        out["sdks"][name] = {"verdict": "BLOCKED" if reasons else "READY", "reasons": reasons, "release_note": note, "status": e["status"]}
    blocked = [n for n, v in out["sdks"].items() if v["verdict"] == "BLOCKED"]
    out["verdict"] = "BLOCKED" if blocked or out["problems"] else "READY"
    out["blocked"] = blocked
    out["release_blocked"] = sorted(n for n, v in out["sdks"].items() if v.get("release_note"))
    return out
