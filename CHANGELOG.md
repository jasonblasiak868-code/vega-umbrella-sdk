# Changelog

## 2026-10-20: fixes found by a source read

These were found by reading the source against its own documentation after release, not by the earlier test and review passes. Each fix has a regression test in
`tests/test_findings_20261020.py` that failed before the fix, and each fix was checked by undoing it and confirming a test fails. Behaviour that changed is listed under "Changed".

### Added
- **The Organism now wires the rest of the family.** Before, it assembled only six kits (terminal, reasoning, council, metacog, trace, feed); the harness, Kronos, pareah, identity, journal, jurisdiction, proof of need, training and sealing each built their own ledger and approval check when used alone. It now builds them from the one ledger, one `Commit` and one chain per kit (see the README section "What the Organism wires"), and `commit_for()` turns a human signature into a minted commitment any gate can check.
- **Integration tests** (`tests/test_integration_20261020.py`, 13 tests) that cross kit boundaries on one organism: a human-only Conductor step on a commitment from the shared ledger, the pipeline asking the arsenal and recording its prompt layers, the frozen path on two commitments, a Kronos job bound to its exact job, the hard stop lifted only by the human key, a revoked PRE stopping an open connection, identity and journal on their lanes under one anchor.
- The umbrella now declares seventeen family dependencies (it declared eight).

### Fixed
- `Organism.metacog_ledger(author, human_check=None)` passes a human check through to the requirements ledger (human requirements cannot be settled without one).
- **Docs:** the README said "Seventeen kits"; the registry holds 22 shipped kits and one design-only entry.
