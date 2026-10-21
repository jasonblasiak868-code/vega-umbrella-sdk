"""registry.py - the family map: every SDK, the one concern it OWNS, what it needs, and how finished it is.

The point of the umbrella is that the family is one stack and not fifteen competing ones, so each concern has exactly one owner and every other SDK uses that owner instead of growing its own copy.
A new SDK must claim a concern nobody owns (or be refused by check_registry): two SDKs may not own the same concern, and a dependency may only point DOWN the layers, never up or sideways into a cycle.
status: BUILT (code and tests exist), PARTIAL (core built, named parts missing), DESIGN (written down, no code)."""
import re

LAYERS = ("record", "authority", "seal", "adapt", "contain", "memory", "conduct", "knowledge", "learn", "interface", "observe", "reason", "verify", "watch", "deliberate", "assemble")

# name -> dict(package, layer index, owns, requires, status, note)
FAMILY = {
    "vega-custody-sdk": dict(package="vega_custody", layer=0, owns="records and chain of custody (capsules, DAG, ledger, safe paths, bounded processes)", requires=[], status="BUILT"),
    "vega-governance-jacket-sdk": dict(package="vega_jacket", layer=1, owns="human authority: human-only actions, single-use signed commitments, entry and exit gates", requires=["vega-custody-sdk"], status="BUILT"),
    "vega-superproof-sdk": dict(package="vega_superproof", layer=2, owns="layered sealing and proof tiers", requires=["vega-custody-sdk"], status="PARTIAL", note="proof tiers 1-2, PQ signatures and FHE are fail-closed interfaces"),
    "vega-identity-sdk": dict(package="vega_identity", layer=3, owns="who is at the door: factors, questions from the user's own knowledge graph and the assurance level each action needs", requires=["vega-custody-sdk", "vega-governance-jacket-sdk"], status="BUILT"),
    "vega-pareah-sdk": dict(package="vega_pareah", layer=3, owns="adapters, cards and quarantine of inbound code", requires=["vega-custody-sdk", "vega-governance-jacket-sdk"], status="BUILT"),
    "vega-two-gate-sdk": dict(package="vega_twogate", layer=4, owns="containment between two gates (Kronos) and the hard stop", requires=["vega-custody-sdk", "vega-governance-jacket-sdk"], status="BUILT"),
    "vega-librarian-sdk": dict(package="vega_librarian", layer=5, owns="lessons and memory of past incidents", requires=["vega-custody-sdk"], status="BUILT"),
    "vega-harness-sdk": dict(package="vega_harness", layer=6, owns="deterministic workflow conduct, pre-registered paths and the library use gate", requires=["vega-custody-sdk", "vega-governance-jacket-sdk", "vega-librarian-sdk"], status="BUILT"),
    "vega-dkg-lattice-sdk": dict(package="vega_dkg", layer=7, owns="the knowledge graph and repo-library processing", requires=["vega-custody-sdk"], status="PARTIAL", note="graph side built; the predictive lattice side lives in vega-reasoning-sdk predict.py and the galaxy repo is queued"),
    "vega-train-sdk": dict(package="vega_train", layer=8, owns="governed model training and freeze cards", requires=["vega-custody-sdk", "vega-governance-jacket-sdk", "vega-harness-sdk", "vega-pareah-sdk", "vega-dkg-lattice-sdk", "vega-superproof-sdk"], status="PARTIAL", note="GPU and LLM trainers are plug-ins, not included"),
    "vega-terminal-sdk": dict(package="vega_terminal", layer=9, owns="gated command execution for people and agents", requires=["vega-custody-sdk", "vega-governance-jacket-sdk"], status="BUILT"),
    "vega-trace-sdk": dict(package="vega_trace", layer=10, owns="telemetry of reasoning: layer traces, entropy, the audible harmonic echo, the reference signature", requires=["vega-custody-sdk"], status="BUILT"),
    "vega-reasoning-sdk": dict(package="vega_reasoning", layer=11, owns="reasoning fidelity, forecasting and routing: the lattice that predicts steps ahead", requires=["vega-custody-sdk"], status="BUILT"),
    "vega-metacog-sdk": dict(package="vega_metacog", layer=12, owns="evidence rungs and the completion gate", requires=["vega-custody-sdk"], status="BUILT"),
    "vega-governance-feed-sdk": dict(package="vega_feed", layer=13, owns="the live view of every chain and the tamper alarms", requires=["vega-custody-sdk"], status="BUILT"),
    "vega-council-sdk": dict(package="vega_council", layer=14, owns="multi-brain deliberation and the design-first builder", requires=["vega-custody-sdk", "vega-harness-sdk"], status="BUILT"),
    "vega-umbrella-sdk": dict(package="vega_umbrella", layer=15, owns="assembly of the family as one organism: one keyed ledger, one approval check, one anchor, the family registry and the pre-deploy audit", requires=["vega-custody-sdk", "vega-governance-jacket-sdk", "vega-terminal-sdk", "vega-trace-sdk", "vega-reasoning-sdk", "vega-metacog-sdk", "vega-governance-feed-sdk", "vega-council-sdk", "vega-harness-sdk", "vega-two-gate-sdk", "vega-pareah-sdk", "vega-identity-sdk", "vega-journal-sdk", "vega-jurisdiction-sdk", "vega-proof-of-need-sdk", "vega-train-sdk", "vega-superproof-sdk"], status="BUILT"),
    # queued by the owner; listed so nothing else claims their concerns
    "vega-galaxy-sdk": dict(package="vega_galaxy", layer=14, owns="the galaxy view of the knowledge lattice: levels, convergence and the future above the present", requires=["vega-custody-sdk", "vega-reasoning-sdk"], status="BUILT"),
    "vega-proof-of-need-sdk": dict(package="vega_need", layer=14, owns="proof of need and of payment: a co-signed constitution, advisory need analysis, human-approved releases from a simulated bankroll and institution receipts", requires=["vega-custody-sdk", "vega-governance-jacket-sdk", "vega-superproof-sdk", "vega-identity-sdk"], status="BUILT", note="paper simulation only: no real money until licensing, KYC and custody gates are cleared"),
    "vega-neural-galaxy-sdk": dict(package="vega_neural", layer=14, owns="the neural galaxy: a model's own layers and traces drawn in 3D, daily traces and training traces side by side", requires=["vega-custody-sdk", "vega-trace-sdk"], status="DESIGN"),
    "vega-journal-sdk": dict(package="vega_journal", layer=14, owns="the private verbatim journal of ideas: encrypted at rest, owner-only, shared or inherited only as the owner decided, grounded answers, last-rites wishes, thought-genome mapper", requires=["vega-custody-sdk", "vega-superproof-sdk"], status="BUILT"),
    "vega-chip-sdk": dict(package="vega_chip", layer=14, owns="governance hardware: a software reference model of the Governance Enforcement Unit and the PRE runtime unit, with conformance tests against the jacket", requires=["vega-custody-sdk", "vega-governance-jacket-sdk"], status="BUILT", note="a model, not a circuit: no silicon or FPGA yet"),
    "vega-jurisdiction-sdk": dict(package="vega_jurisdiction", layer=14, owns="jurisdictional protocol keys: branch keys, 2-of-3 policy, the People's Veto and the Kronos root", requires=["vega-custody-sdk", "vega-governance-jacket-sdk"], status="BUILT"),
}
STATUSES = ("BUILT", "PARTIAL", "DESIGN")
_NAME = re.compile(r"vega-[a-z0-9-]+-sdk")


class RegistryRefused(ValueError):
    pass


def check_registry(family=None):
    """Raises RegistryRefused on: a bad name or package, two owners of one concern, a dependency on an unknown SDK, a dependency that points up or sideways to a layer not strictly below, a cycle."""
    fam = FAMILY if family is None else family
    owns, pkgs = {}, {}
    for name, e in fam.items():
        if not _NAME.fullmatch(name) or e.get("status") not in STATUSES or not isinstance(e.get("layer"), int) or isinstance(e.get("layer"), bool) or not 0 <= e["layer"] < len(LAYERS):
            raise RegistryRefused("%s: a bad name, status or layer" % name)
        if not isinstance(e.get("owns"), str) or not e["owns"].strip():
            raise RegistryRefused("%s owns nothing: every SDK owns one concern" % name)
        key = e["owns"].strip().casefold()
        if key in owns:
            raise RegistryRefused("%s and %s own the same concern" % (name, owns[key]))
        owns[key] = name
        if e["package"] in pkgs:
            raise RegistryRefused("%s and %s share the package name %s" % (name, pkgs[e["package"]], e["package"]))
        pkgs[e["package"]] = name
    for name, e in fam.items():
        for d in e["requires"]:
            if d not in fam:
                raise RegistryRefused("%s requires %s, which is not in the family" % (name, d))
            if fam[d]["layer"] >= e["layer"]:
                raise RegistryRefused("%s (layer %d) requires %s (layer %d): a dependency must be on a lower layer" % (name, e["layer"], d, fam[d]["layer"]))
    state = {}

    def visit(n):
        if state.get(n) == 1:
            raise RegistryRefused("dependency cycle through %s" % n)
        if state.get(n) == 2:
            return
        state[n] = 1
        for d in fam[n]["requires"]:
            visit(d)
        state[n] = 2
    for n in fam:
        visit(n)
    return True


def build_order(family=None):
    fam = FAMILY if family is None else family
    check_registry(fam)
    order, seen = [], set()

    def visit(n):
        if n in seen:
            return
        seen.add(n)
        for d in fam[n]["requires"]:
            visit(d)
        order.append(n)
    for n in sorted(fam, key=lambda k: (fam[k]["layer"], k)):
        visit(n)
    return order
