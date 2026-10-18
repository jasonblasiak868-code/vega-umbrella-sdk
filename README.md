# vega-umbrella-sdk

## The AI paradox, and one answer to it

**The paradox.** The more an AI can do for you, the more it can do to you. Autonomy is what makes it useful. Unchecked autonomy is what makes it unsafe. And asking the model to police itself fails for a simple reason: the thing being checked is also doing the checking. Most of today's answers are policies, promises and prompts, and none of them is something you can verify.

**The answer in one sentence.** Authority to act stays with a human and is spent one action at a time: nothing consequential runs unless a person has signed a single-use, time-limited commitment that names that exact action, and everything else is written to a tamper-evident record that anyone can check without trusting the model, the vendor or this project.

This is governance above the model, not inside it. The model can reason, plan and draft freely. It cannot act on the world, and it cannot give itself permission to.

**What this family of kits addresses** (each is a working, tested reference implementation, not a finished product):

| The concern people raise | What addresses it here |
|---|---|
| Who authorised that action? | Human-signed single-use commitments; a gate that refuses without one (governance-jacket, two-gate) |
| Can the AI authorise itself or widen its own powers? | No agent can mint or extend a commitment; authority is non-transitive (governance-jacket, pareah) |
| Can I prove afterwards what happened, and that nothing was altered? | An append-only, hash-chained record of custody, plus sealed evidence (custody, superproof) |
| What if an unknown or hostile agent connects? | An adapter that admits only what the owner announced and holds everything else in a dead end (pareah) |
| Where did the knowledge and the training data come from? | A licence-aware knowledge graph and governed training that records exactly what a model learned from (dkg-lattice, train, librarian) |
| Is the reasoning sound, and did it read what it claims it read? | Pre-execution reasoning checks, meta-audit and traces (reasoning, metacog, trace) |
| Can I see and steer it? | A visible galaxy of what the system knows, a governed terminal and a live governance feed (galaxy, terminal, governance-feed) |

**What this is not.** It is not a complete solution to AI risk, and it does not make a model aligned, truthful or kind. It does not replace a lawyer, an auditor or an independent security review: none of the cryptography or protocol code here has had an independent expert review. These are software reference models; the hardware designs are not built. It narrows one specific and important gap: the distance between "the AI decided" and "a human authorised".

Patent pending (U.S. provisional application 64/178,949 and others). Source-available under the licence in LICENSE: free for personal use and for registered small businesses, a commercial licence otherwise. The licence text is a draft that has not been reviewed by an attorney.


![vega-umbrella-sdk](assets/tile.svg)

The umbrella: assembles the SDK family as one organism (one keyed ledger, one approval check, one anchor over every chain), a registry of owned concerns, and a pre-deploy audit gate.

> **Licensing.** Source-available, not open source. Free for personal use; free for registered small businesses (under US$1M revenue and valuation); everyone else needs a commercial license (see LICENSE; for a commercial license write to jasonblasiak.ai.mail@gmail.com). Patent pending. Draft licence text, not yet reviewed by an attorney.

Package: `vega_umbrella` (src layout). Depends on: vega-custody-sdk, vega-governance-jacket-sdk.

## Modules

| Module | What it does |
|---|---|
| `registry` | Every SDK, the one concern it owns, its layer and status; two owners of a concern, an upward dependency or a cycle are refused. |
| `organism` | One human public key, one keyed ledger, one exit gate and one approval check shared by terminal, council, builder, router and overseer; per-lane chains plus an anchor chain. |
| `audit` | Read-only pre-deploy audit: licence hash, commercial licence, review findings, test pass, declared dependencies, unfiled-matter release block. |
| `feedback` | The feedback icon's engine: builds an email draft (a mailto link) addressed to the owner with the subject naming the system it came from, refuses anything that looks like a key, attaches nothing, and never sends by itself; the user reads and sends it from their own mail program. |
| `__main__` | status, order and audit from the command line. |

## What it does NOT do (read this)

- Feedback is a draft the user sends themselves: no mail password is carried in the software, and the owner's address must be configured before any draft can be built.
- It never signs anything; the human signs in their own terminal and the umbrella only presents the signature.
- A deployment that bypasses the Organism and builds its own ledger loses the guarantee.
- READY from the audit means nothing it checks is in the way; it does not publish and cannot lift a release block.

## Status

See STATUS.md. Tests: 61 tests in 5 files, all passing.  See SECURITY.md for the threat model.

## Run the tests

Put `src` of this repo and of the repos it depends on on PYTHONPATH, then run each file in `tests/`.
