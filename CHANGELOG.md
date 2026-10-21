# Changelog

## 2026-10-20: fixes found by a source read

These were found by reading the source against its own documentation after release, not by the earlier test and review passes. Each fix has a regression test in
`tests/test_findings_20261020.py` that failed before the fix, and each fix was checked by undoing it and confirming a test fails. Behaviour that changed is listed under "Changed".

### Fixed
- `Organism.metacog_ledger(author, human_check=None)` passes a human check through to the requirements ledger (human requirements cannot be settled without one).
- **Docs:** the README said "Seventeen kits"; the registry holds 22 shipped kits and one design-only entry.
