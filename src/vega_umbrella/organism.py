"""organism.py - the whole family assembled as one organism around ONE human key, ONE keyed ledger and ONE record.

Why this exists: the SDKs are each usable alone, but run together they would each build their own chain, ledger and approval check, and the weakest of those would define the whole. The Organism builds the
shared pieces once and hands them to every SDK that needs them:
  - ONE keyed ledger: it refuses to mint or verify a commitment that the human key did not sign (the fix for a ledger that trusts whoever holds it). A deployment that does not use the Organism must build
    its ledger the same way, or the guarantee is gone.
  - ONE exit gate (single-use, exact-action, human-signed) and ONE place that turns a signature into a yes: approvals(). The paid-lane check, the design approval, the taste decision and the overseer
    co-sign of the other SDKs are all asked of THIS object, so there is one rule for 'did the human say yes to exactly this'.
  - one custody chain per lane (terminal, reasoning, council, ...) under one folder, plus an ANCHOR chain that records every lane's head hash, so one root hash covers the whole organism and the
    feed can watch all of it.
Nothing here signs anything: signatures are made by the human, in their own terminal, and only presented. Each SDK is imported only when its lane is asked for, so using one SDK alone never needs the rest."""
import hashlib
import json
import os
import re
import threading

from vega_custody import safepaths as sp
from vega_custody.dag.dag import Dag, RecordRefused
from vega_custody.ledger.backend_local import LocalBackend
from vega_custody.ledger.ledger import Ledger

_LANE = re.compile(r"[a-z][a-z0-9_]{0,31}")
PRESENT_CAP = 256
PER_KEY_CAP = 4


class OrganismRefused(ValueError):
    pass


def _h(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()        # strict: an object that is not plain data raises instead of being hashed by its repr


class Approvals:
    """Pending human approvals, each keyed by the exact (action, params) it was signed for. take() runs the exit gate and so burns the signature: one approval, one use."""

    def __init__(self, gate, precheck):
        """precheck() returns a FRESH verifier (a new used-nonce set each time), so looking at a signature at the door never spends it; spending happens only in the gate, in take()."""
        self.gate, self._precheck, self._pending, self._lock = gate, precheck, {}, threading.Lock()

    def present(self, action, params, signed):
        if not isinstance(action, str) or not isinstance(params, dict) or not isinstance(signed, dict):
            raise OrganismRefused("an approval is (action, params, signed)")
        try:
            k = _h([action, params])
        except (TypeError, ValueError):
            raise OrganismRefused("params must be plain data")
        try:
            self._precheck().check(action, params, signed)                    # only a genuine human signature for exactly this action and these parameters may occupy a slot
        except Exception:
            raise OrganismRefused("that is not a valid human signature for this action and these parameters")
        with self._lock:
            if sum(len(v) for v in self._pending.values()) >= PRESENT_CAP:
                raise OrganismRefused("too many pending approvals")
            slot = self._pending.setdefault(k, [])
            if len(slot) >= PER_KEY_CAP:
                raise OrganismRefused("too many approvals offered for this one action")
            slot.append(signed)                                               # several may be offered for one action: a garbage one cannot push a real one out

    def take(self, action, params):
        try:
            k = _h([action, params])
        except (TypeError, ValueError):
            return False
        while True:
            with self._lock:
                slot = self._pending.get(k)
                if not slot:
                    self._pending.pop(k, None)
                    return False
                signed = slot.pop(0)
            try:
                self.gate.release(action, params, signed, route="human")
                return True
            except Exception:
                continue                                                      # that one was no good: try the next one offered; any refusal, from any cause, is a no for THAT one

    # the checks the other SDKs ask for, all answered here -------------------------------------------------
    def paid_ok(self, lane, query_sha256):
        """council and MoRNA ask this before a paid lane is touched: a human-signed spend_funds for exactly this lane and query."""
        return self.take("spend_funds", {"lane": lane, "query_sha256": query_sha256})

    def design_ok(self, design_sha256):
        return self.take("approve_design", {"design_sha256": design_sha256})

    def decision_ok(self, token_sha256):
        return self.take("decide_taste", {"token_sha256": token_sha256})

    def cosign_ok(self, verdict_sha256):
        return self.take("cosign_promotion", {"verdict_sha256": verdict_sha256})


class Organism:
    def __init__(self, home, public_key, device, surface, human_verifier=None):
        """home: folder for every chain. public_key: the human's PUBLIC key (never a private one). device and surface name where approvals may be spent."""
        from vega_jacket import humanauth
        from vega_jacket.commit.commit import Commit
        from vega_jacket.gate.exit_gate import ExitGate
        from vega_jacket.humanauth import verify
        self.home = os.path.realpath(home)
        os.makedirs(self.home, exist_ok=True)
        self.dag = self._chain("anchor")
        self.ledger = Ledger([LocalBackend(os.path.join(self.home, "ledger.jsonl"))], commitment_check=verify.commitment_signature_checker(public_key))
        self.verifier = human_verifier or humanauth.Verifier(public_key, device, surface)
        self.gate = ExitGate(Commit(self.verifier, self.ledger, self.dag), self.ledger, self.verifier, self.dag)
        self.approvals = Approvals(self.gate, lambda: humanauth.Verifier(public_key, device, surface))
        self._lanes = {}

    def _chain(self, lane):
        if not _LANE.fullmatch(lane):
            raise OrganismRefused("a lane name is lowercase letters, digits and underscores")
        d = os.path.join(self.home, "chains")
        os.makedirs(d, exist_ok=True)
        return Dag([os.path.join(d, lane + ".content.jsonl")], [os.path.join(d, lane + ".locations.jsonl")])

    def lane(self, name):
        """The custody chain of one lane, created on first use."""
        if name not in self._lanes:
            self._lanes[name] = self._chain(name)
        return self._lanes[name]

    def lane_paths(self):
        """What the governance feed should watch: the anchor and every lane that exists."""
        d = os.path.join(self.home, "chains")
        out = {"anchor": [os.path.join(d, "anchor.content.jsonl")]}
        for n in self._lanes:
            out[n] = [os.path.join(d, n + ".content.jsonl")]
        return out

    def anchor(self):
        """Record every lane's current head hash on the anchor chain. The anchor's own head then commits to the whole organism at this moment."""
        heads = {n: (dag.content.head() or "") for n, dag in sorted(self._lanes.items())}
        try:
            e = self.dag.record("ORGANISM_ANCHOR", {"lanes": sorted(heads), "heads": heads, "root_sha256": _h(heads)})
        except RecordRefused as exc:
            raise OrganismRefused(str(exc))
        return {"root_sha256": _h(heads), "anchor_entry": e["entry_hash"], "heads": heads}

    def verify_all(self):
        out, ok = {}, True
        for name, dag in [("anchor", self.dag)] + sorted(self._lanes.items()):
            good, problems = dag.verify()
            out[name] = problems
            ok = ok and good
        return {"ok": ok, "problems": {k: v for k, v in out.items() if v}}

    # lazy factories: each imports only the SDK it needs -----------------------------------------------------
    @staticmethod
    def _need(module):
        """The module for one lane, imported only now and only from a fixed list (each entry is a plain import statement, so no import ever comes from a variable)."""
        importer = _IMPORTERS.get(module)
        if importer is None:
            raise OrganismRefused("%s is not a lane of the organism" % module)
        try:
            return importer()
        except ImportError as exc:
            raise OrganismRefused("this lane needs %s, which is not installed (%s)" % (module, exc))

    def terminal(self, workspace, timeout=30.0):
        m = self._need("vega_terminal.session")
        return m.Session(workspace, self.lane("terminal"), self.gate, timeout=timeout)

    def reasoning_log(self):
        return self._need("vega_reasoning.records").ReasoningLog(self.lane("reasoning"))

    def router(self, lanes, rows_fn):
        return self._need("vega_reasoning.morna").Router(lanes, rows_fn, self.lane("reasoning"), paid_ok=self.approvals.paid_ok)

    def mri(self):
        return self._need("vega_reasoning.lyra").MRI(self.lane("reasoning"))

    def council(self, brains):
        return self._need("vega_council.deliberation").Council(brains, self.lane("council"), paid_ok=self.approvals.paid_ok)

    def builder(self):
        return self._need("vega_council.builder").Builder(self.lane("council"))

    def library(self, root, matrix=None):
        return self._need("vega_council.library").ReferenceLibrary(root, self.lane("council"), matrix)

    def metacog_ledger(self, author, human_check=None):
        """human_check(requirement id, verifier id) -> exactly True settles a 'human' requirement; without one no human requirement can be settled (fails closed)."""
        return self._need("vega_metacog.requirements").Ledger(self.lane("metacog"), author, human_check=human_check)

    def trace_chain(self):
        return self.lane("trace")

    def observe_ledger(self):
        return self._need("vega_trace.nnr").ObserveLedger(self.lane("trace"))

    def feed(self, state_path=None):
        """A governance feed over the anchor and every lane that exists NOW (build it after the lanes it should watch)."""
        return self._need("vega_feed.feed").Feed(self.lane_paths(), state_path=state_path)


def _terminal_session():
    import vega_terminal.session as m
    return m


def _reasoning_records():
    import vega_reasoning.records as m
    return m


def _reasoning_morna():
    import vega_reasoning.morna as m
    return m


def _reasoning_lyra():
    import vega_reasoning.lyra as m
    return m


def _council_deliberation():
    import vega_council.deliberation as m
    return m


def _council_builder():
    import vega_council.builder as m
    return m


def _council_library():
    import vega_council.library as m
    return m


def _metacog_requirements():
    import vega_metacog.requirements as m
    return m


def _trace_nnr():
    import vega_trace.nnr as m
    return m


def _feed_feed():
    import vega_feed.feed as m
    return m


_IMPORTERS = {"vega_terminal.session": _terminal_session, "vega_reasoning.records": _reasoning_records, "vega_reasoning.morna": _reasoning_morna, "vega_reasoning.lyra": _reasoning_lyra, "vega_council.deliberation": _council_deliberation, "vega_council.builder": _council_builder, "vega_council.library": _council_library, "vega_metacog.requirements": _metacog_requirements, "vega_trace.nnr": _trace_nnr, "vega_feed.feed": _feed_feed}
