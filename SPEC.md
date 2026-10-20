# vega-umbrella-sdk — Specification

Spec v1.0 — 2026-10-20 — describes the published reference implementation as tested. Where this document and the source disagree, the source wins.

**Contents:** [Purpose](#1-purpose-and-scope) · [Vocabulary](#2-vocabulary) · [Components](#3-components) · [Guarantees](#4-guarantees-and-non-guarantees) · [Failure modes](#5-failure-modes) · [Interfaces](#6-interfaces-and-diagnostics)

## 1. Purpose and scope

Specified: the family registry and its rules, the Organism that assembles the kits around one human key, one keyed ledger and one approval check, the read-only pre-deploy audit, and the feedback-draft builder. Out of scope: signing (the human does it elsewhere), publishing, sending mail, and the behavior of the individual kits.

## 2. Vocabulary

| Term | Meaning |
|---|---|
| Concern | The one job a kit owns. No two kits may own the same concern. |
| Layer | An index from 0 (record) to 15 (assemble). Dependencies must point to a strictly lower layer. |
| Status | BUILT, PARTIAL or DESIGN, as recorded in the registry. |
| Organism | The assembled family: shared ledger, exit gate and approvals, plus one chain per lane. |
| Lane | A named custody chain for one part of the family, for example terminal or council. |
| Anchor | A chain that records each lane's head hash so one root covers all lanes. |
| Approvals | Pending human approvals keyed by the exact action and parameters they were signed for. |
| Audit verdict | READY or BLOCKED, with reasons. |

## 3. Components

### 3.1 `registry`

**Interface.** `FAMILY`, `LAYERS`, `STATUSES`, `check_registry`, `build_order`, `RegistryRefused`.

**Behavior.** Each entry has a package name, layer, owned concern, requirements and status. `check_registry` refuses: a bad name, status or layer; an entry that owns nothing; two kits owning the same concern; two kits sharing a package name; a requirement on an unknown kit; a requirement that does not point to a strictly lower layer; and any cycle. `build_order` returns a dependency-first list after the check passes. The registry also lists kits that are not part of this release so nothing else claims their concerns.

### 3.2 `organism`

**Interface.** `Organism`, `Approvals`, `OrganismRefused`, `PRESENT_CAP` 256, `PER_KEY_CAP` 4.

**Behavior.**
- `Organism(home, public_key, device, surface, ...)` builds one keyed ledger that refuses to mint or verify a commitment the human key did not sign, and one exit gate.
- `lane(name)` gives a custody chain for a lane. Lane names match a short lowercase pattern. `anchor()` records every lane head; `verify_all()` checks every chain.
- Accessors build a lane's kit only when asked (`terminal`, `reasoning_log`, `router`, `mri`, `council`, `builder`, `library`, `metacog_ledger`, `trace_chain`, `observe_ledger`, `feed`). A kit that is not installed is not imported until its lane is requested.
- `Approvals.present(action, params, signed)` looks at a signature without spending it. `take(action, params)` runs the exit gate and burns the signature: one approval, one use. Helpers `paid_ok`, `design_ok`, `decision_ok` and `cosign_ok` are the single place the other kits ask "did the human say yes to exactly this".

**Invariants.** Nothing in the umbrella signs. A signature is single-use and exact-action.

### 3.3 `audit`

**Interface.** `audit_family(root, canonical_license_sha256, public_eligible=None)`.

**Behavior.** Read-only. Reports per kit and overall: registry soundness; each BUILT or PARTIAL kit present on disk with dependencies covering the registry; the licence file matching the canonical hash; review findings with no high or medium item; tests run and passed; and release blocks tied to matter the owner has not cleared. It reports a block; it never lifts one.

### 3.4 `feedback`

**Interface.** `FeedbackConfig`, `build_message`, `parse_mailto`, `known_system`, `FeedbackRefused`, `MAX_TEXT` 4000, `MAX_LINK` 1800.

**Behavior.** Builds a `mailto:` draft addressed to the configured owner address with a subject naming the originating system. Refuses empty or over-long text and text that looks like a key or token, strips control characters, shortens the link when long and reports `truncated`. Attaches nothing and never sends.

### 3.5 `__main__`

`python -m vega_umbrella status | order | audit ROOT LICENSE_SHA256`. Read-only; prints JSON. Exit code 2 for bad usage; for `audit`, 0 only on READY.

## 4. Guarantees and non-guarantees

| Guarantee | Module | Evidence |
|---|---|---|
| One owner per concern; dependencies point down; no cycles | `registry` | `tests/redteam_1_registry_and_audit.py` |
| The ledger refuses commitments the human key did not sign | `organism` | `tests/redteam_2_approvals.py` |
| An approval is spent once and only for its exact action | `organism.Approvals` | `tests/redteam_2_approvals.py` |
| The audit never writes | `audit` | `tests/redteam_1_registry_and_audit.py` |
| Feedback never sends and refuses key-shaped text | `feedback` | `tests/test_feedback.py` |

| Non-guarantee | Reality |
|---|---|
| READY means safe | No. It means nothing the audit checks is in the way. |
| A custom ledger is protected | No. Bypassing the Organism drops the guarantee. |
| The registry proves behavior | No. It records claims; the audit checks files and metadata. |

## 5. Failure modes

| Event | What happens |
|---|---|
| Registry entry malformed, duplicate concern, upward dependency, cycle | `RegistryRefused` |
| Commitment not signed by the human key | Refused by the keyed ledger |
| Approval reused or for a different action | Refused |
| Required kit not installed when its lane is requested | `OrganismRefused` naming the missing module |
| Audit finds a problem | BLOCKED with reasons, exit code 1 |
| Feedback contains a key-shaped string | `FeedbackRefused` |

## 6. Interfaces and diagnostics

Command line as above. No environment variables are read by the registry or audit. The owner feedback address is a constant in `feedback`.
