"""pretooluse_gate.py - a deny-by-default gate for an agent CLI's shell tool, in the form Claude Code's PreToolUse hooks take.

Claude Code runs a hook command before a tool call and sends the call as JSON on standard input; exit code 2 blocks the call and the text on standard error is shown to the model.
(Check the current Claude Code hooks documentation for the exact fields; other agent CLIs have their own hook or wrapper mechanisms.)

This script allows a shell command only if it matches a rule in allow.json next to it, and writes each decision (hashes only) to a custody chain if vega-custody-sdk is installed.
It is a starting pattern, not the full governance gate: a real deployment would require a human-signed single-use commitment for anything outside the allow-list (see vega-governance-jacket-sdk).
allow.json:  {"allow_prefixes": ["git status", "git diff", "python -m unittest"]}
"""
import hashlib
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).parent


def decide(payload, allow):
    if payload.get("tool_name") != "Bash":
        return True, "not a shell call"
    cmd = str((payload.get("tool_input") or {}).get("command", "")).strip()
    if any(ch in cmd for ch in ";&|`$<>\n"):
        return False, "shell metacharacters need a human approval"
    ok = any(cmd == p or cmd.startswith(p + " ") for p in allow.get("allow_prefixes", []))
    return ok, "allowed by rule" if ok else "not on the allow-list"


def record(cmd, ok):
    try:
        from vega_custody.dag.dag import Dag
        d = pathlib.Path(os.environ.get("VEGA_GATE_LOG", HERE / "gate-log"))
        d.mkdir(parents=True, exist_ok=True)
        Dag([d / "c.jsonl"], [d / "l.jsonl"]).record("GATE_DECISION", {"command_sha256": hashlib.sha256(cmd.encode()).hexdigest(), "allowed": ok})
    except Exception:
        pass                                                   # logging must never turn a deny into an allow, nor crash the hook


def main():
    try:
        payload = json.load(sys.stdin)
        allow_path = HERE / "allow.json"
        allow = json.loads(allow_path.read_text()) if allow_path.exists() else {}
    except Exception:
        print("gate could not read its input: refusing", file=sys.stderr)
        return 2                                               # fail closed
    ok, why = decide(payload, allow)
    record(str((payload.get("tool_input") or {}).get("command", "")), ok)
    if not ok:
        print("Blocked by the gate: %s." % why, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
