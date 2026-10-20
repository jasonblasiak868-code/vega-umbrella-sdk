# vega-umbrella-sdk — Capabilities

Each row says what the capability is, why a policy or prompt-level approach cannot give it, where this code enforces it, which test shows it, and the honest limit.

| Capability | Why a policy or prompt cannot provide it | Enforced in | Test | Honest limit |
|---|---|---|---|---|
| One owner per concern | A style guide asks kits not to overlap; the registry refuses the second owner | `registry.check_registry` | `tests/redteam_1_registry_and_audit.py` | Concern names are free text that must differ |
| Downward-only dependencies | "No circular imports" is a request; the check rejects any dependency that is not on a lower layer | `registry.check_registry` | `tests/redteam_1_registry_and_audit.py` | Checks declared dependencies, not actual imports |
| Dependency-first order | A deployment order written in prose drifts; this is computed | `registry.build_order` | `tests/test_umbrella.py` | None beyond the registry's accuracy |
| One keyed ledger | Trusting whoever holds the ledger lets the weakest copy define the whole; this ledger refuses what the human key did not sign | `organism.Organism` | `tests/redteam_2_approvals.py` | A deployment that builds its own ledger loses it |
| One approval check | Each kit inventing its own "did the human agree" check creates gaps; all ask one object | `organism.Approvals` | `tests/redteam_2_approvals.py` | The human can still approve carelessly |
| Single-use, exact-action approvals | A reusable "approved" flag can be replayed; the signature is burned on use | `Approvals.take` | `tests/redteam_2_approvals.py` | Depends on the jacket kit's gate |
| One root over every lane | Separate chains can each be intact while disagreeing; the anchor records every head | `Organism.anchor`, `verify_all` | `tests/test_umbrella.py` | The anchor lives with the same keeper unless replicated |
| Read-only pre-deploy audit | A checklist in a document is not run; the audit reads folders and reports | `audit.audit_family` | `tests/redteam_1_registry_and_audit.py` | Checks files and metadata, not behavior |
| Feedback that cannot leak a key | A reminder not to paste secrets is ignored; key-shaped text is refused | `feedback.build_message` | `tests/test_feedback.py` | Pattern-based, so unusual secrets can pass |
| No silent send | A mailer in the software would need a password inside it; this builds a draft the user sends | `feedback` | `tests/test_feedback.py` | The user must read and send it |

## Its part in the family loop

The umbrella does not add a new kind of work. It makes the others one system: records flow to memory and knowledge, knowledge feeds reasoning and the galaxy view, the harness and metacog gate what counts as done, the feed shows everything to the human, and the human decides again. The umbrella's job is to ensure all of that uses one key, one ledger and one approval rule.

See [README.md](README.md), [SPEC.md](SPEC.md), [ARCHITECTURE.md](ARCHITECTURE.md) and [ORGANISM.md](ORGANISM.md).
