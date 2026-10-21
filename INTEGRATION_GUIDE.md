# Integration guide: installing the kits and putting them above your models and agent CLIs

The Vega kits are Python libraries. They do not call any model or network service themselves. You supply the model calls, and the kits decide what may enter and leave around them. This guide shows how to install them on common systems, how to connect them to models, and how to put a gate in front of an agent command-line tool.

> **Where to find this guide.** The home page of this GitHub account explains what is here and points to this file, which lives in the `vega-umbrella-sdk` build. Each kit's README opens with its own build-order banner.

**Contents:** [What is tested](#what-was-tested-and-what-was-not) · [1 The idea in one minute](#1-the-idea-in-one-minute) · [2 Install on your system](#2-install-on-your-system) · [3 Connect models](#3-connect-models) · [4 Run the council on real models](#4-run-the-council-on-real-models) · [5 Put a gate in front of an agent CLI](#5-put-a-gate-in-front-of-an-agent-cli) · [6 Keys](#6-keys-and-secrets) · [7 Limits](#7-limits)

## What was tested and what was not

| Part of this guide | Status |
|---|---|
| `pip install` of a kit straight from its GitHub address | Tested for `vega-custody-sdk` |
| Council run with stand-in models (`council_any_model.py --demo`) | Tested |
| The model adapter (`openai_compat.py`) against a local mock server | Tested against a mock only |
| The shell-command gate (`pretooluse_gate.py`) deciding allow, deny and bad-input cases | Tested by feeding it sample calls |
| Calls to real providers, Docker, macOS, Android and iOS, and registering the gate in a live agent CLI | **Not tested here.** Treat those steps as a starting point and check each tool's current documentation. |

## 1. The idea in one minute

Three places matter: the **model calls** you make, the **tool calls** an agent wants to make, and the **approvals** a person gives. The kits guard the second and third. A model may think and propose freely; anything that changes something outside waits for a person's single-use approval, and every step goes on a tamper-evident record. See [ORGANISM.md](ORGANISM.md) for the map of the kits.

## 2. Install on your system

You need Python 3.10 or newer. Install the kits **in dependency order with `--no-deps`** (the kits are not on PyPI, so pip cannot resolve their family dependencies by name). Custody comes first, then the governance jacket, then the kits that need them. Each kit's README names its requirements. Never run a plain `pip install vega-custody-sdk`: that name is not published here, and installing it from an index you do not control is not safe.

| System | Steps |
|---|---|
| **Windows** | `python -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, then `pip install --no-deps git+https://github.com/jasonblasiak868-code/vega-custody-sdk` and the same for each next kit. |
| **macOS, Linux, WSL** | `python3 -m venv .venv`, `source .venv/bin/activate`, then the same `pip install --no-deps git+https://github.com/jasonblasiak868-code/<kit>` lines. |
| **Docker** | Start from a `python:3.12-slim` image, `RUN pip install --no-deps git+https://github.com/jasonblasiak868-code/<kit>` for each kit in order, then copy your code in. Pin each install to a commit (`@<commit>`) for repeatable builds. |
| **CI** | The same pip lines in a job step. Run each kit's tests with `python -m unittest discover -s tests` after cloning it. |
| **Android** | No native build is published. Use Termux (`pkg install python git`) and the Linux steps. |
| **iOS** | No native build is published. Only a Python runtime that supports the kits' dependencies (for example the BeeWare or Pythonista tooling) could run them. |
| **VS Code** | See [USE_IN_VS_CODE.md](USE_IN_VS_CODE.md). |

Two kits need extra packages: anything that seals data uses `cryptography`. Install it with `pip install cryptography`.

## Install order for every kit

Every kit's README starts with a banner like **Build order 5/5** that lists exactly what to install first. The same information in one table (generated from each kit's declared dependencies):

| Kit | What it does | Build order | Install these first (in order) |
|---|---|---|---|
| [custody](https://github.com/jasonblasiak868-code/vega-custody-sdk) | Tamper-evident chain of custody for AI actions: capsules, hash-chained ledger, safe paths, bounded processes. | 1/1 | none |
| [governance-feed](https://github.com/jasonblasiak868-code/vega-governance-feed-sdk) | Live view of every governance chain with tamper alarms. | 2/2 | `custody` |
| [governance-jacket](https://github.com/jasonblasiak868-code/vega-governance-jacket-sdk) | Human-only authority for AI agents: single-use, time-limited signed commitments with entry and exit gates. | 2/2 | `custody` |
| [librarian](https://github.com/jasonblasiak868-code/vega-librarian-sdk) | Lessons and memory of past incidents so an AI system learns from what went wrong. | 2/2 | `custody` |
| [metacog](https://github.com/jasonblasiak868-code/vega-metacog-sdk) | Evidence rungs and a completion gate: an AI cannot claim done without the evidence. | 2/2 | `custody` |
| [reasoning](https://github.com/jasonblasiak868-code/vega-reasoning-sdk) | Reasoning fidelity, forecasting and routing: a lattice that predicts steps ahead. | 2/2 | `custody` |
| [superproof](https://github.com/jasonblasiak868-code/vega-superproof-sdk) | Layered sealing and proof tiers for private data: zero-knowledge interfaces, updatable encryption, fail-closed tiers. | 2/2 | `custody` |
| [trace](https://github.com/jasonblasiak868-code/vega-trace-sdk) | Telemetry of AI reasoning: layer traces, entropy, harmonic echo and a reference signature. | 2/2 | `custody` |
| [chip](https://github.com/jasonblasiak868-code/vega-chip-sdk) | Governance hardware reference model in software: a Governance Enforcement Unit and a runtime unit that enforce human-signed, single-use commitments, w | 3/3 | `custody`, `governance-jacket` |
| [galaxy](https://github.com/jasonblasiak868-code/vega-galaxy-sdk) | The galaxy view of a knowledge lattice: necessary conditions from below, possible futures from above. | 3/3 | `custody`, `reasoning` |
| [identity](https://github.com/jasonblasiak868-code/vega-identity-sdk) | Identity verification for AI-governed systems: passwords, authenticator codes, phone codes, voice and biometric match, knowledge-graph questions, and  | 3/3 | `custody`, `governance-jacket` |
| [journal](https://github.com/jasonblasiak868-code/vega-journal-sdk) | A private, encrypted, hash-chained question-and-answer journal with a thought-genome map: every idea anchored to its first appearance, with Merkle rec | 3/3 | `custody`, `superproof` |
| [jurisdiction](https://github.com/jasonblasiak868-code/vega-jurisdiction-sdk) | Jurisdictional protocol keys for AI governance: branch keys, a 2-of-3 policy, a public veto and the hard-stop root, so legal minimums are enforced in  | 3/3 | `custody`, `governance-jacket` |
| [terminal](https://github.com/jasonblasiak868-code/vega-terminal-sdk) | Gated command execution for people and AI agents: nothing runs without an approved commitment. | 3/3 | `custody`, `governance-jacket` |
| [two-gate](https://github.com/jasonblasiak868-code/vega-two-gate-sdk) | Kronos: two-gate containment for any program or AI agent, with a verified kill, verified teardown and a hard stop only the human key can lift. | 3/3 | `custody`, `governance-jacket` |
| [harness](https://github.com/jasonblasiak868-code/vega-harness-sdk) | Deterministic agent workflow harness: pre-registered paths, licence use gate, replayable conduct. | 4/4 | `custody`, `governance-jacket`, `librarian` |
| [pareah](https://github.com/jasonblasiak868-code/vega-pareah-sdk) | Adapter and quarantine layer: admits only what the owner announced and holds unknown agents in a dead-end room. | 4/4 | `custody`, `governance-jacket`, `superproof` |
| [council](https://github.com/jasonblasiak868-code/vega-council-sdk) | Anonymous multi-brain deliberation that always carries dissent, plus a design-first builder with human taste decisions. | 5/5 | `custody`, `governance-jacket`, `librarian`, `harness` |
| [dkg-lattice](https://github.com/jasonblasiak868-code/vega-dkg-lattice-sdk) | Licence-aware knowledge graph with provenance for every fact and a predictive lattice. | 5/5 | `custody`, `governance-jacket`, `librarian`, `harness` |
| [proof-of-need](https://github.com/jasonblasiak868-code/vega-proof-of-need-sdk) | Proof of need and proof of payment: a co-signed constitution, advisory need analysis, human-approved releases from a simulated bankroll, institution r | 5/5 | `custody`, `governance-jacket`, `identity`, `superproof` |
| [train](https://github.com/jasonblasiak868-code/vega-train-sdk) | Governed model training that records exactly what a model learned from, with held-out test separation. | 8/8 | `custody`, `governance-jacket`, `librarian`, `harness`, `dkg-lattice`, `superproof`, `pareah` |
| [umbrella](https://github.com/jasonblasiak868-code/vega-umbrella-sdk) | The umbrella that assembles the Vega SDK family as one organism: registry, one keyed ledger, one approval check, pre-deploy audit. | 20/20 | `custody`, `governance-jacket`, `librarian`, `harness`, `council`, `governance-feed`, `identity`, `superproof`, `journal`, `jurisdiction`, `metacog`, `pareah`, `proof-of-need`, `reasoning`, `terminal`, `trace`, `dkg-lattice`, `train`, `two-gate` |

Kits with the same dependencies can be installed in any order among themselves. A kit also needs the extra Python packages named in its banner (for example `cryptography`).

## 3. Connect models

Each "brain", tool or transport in the kits is a function you pass in. `examples/openai_compat.py` is one small function that talks to any server speaking the common chat-completions format:

```python
from openai_compat import make_asker
ask = make_asker("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "a-model-name")
print(ask("Say hello."))
```

| Where the model lives | Base URL pattern | Key |
|---|---|---|
| OpenRouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| A local gateway such as OmniRoute | the gateway's local address ending in `/v1` | the gateway's key, if it needs one |
| Ollama on your machine | `http://localhost:11434/v1` | none |
| Gemini through its OpenAI-compatible endpoint | `https://generativelanguage.googleapis.com/v1beta/openai/` | your Google AI key |
| Anthropic, OpenAI and others, natively | use the provider's own Python library inside your own `ask(prompt)` function | the provider's key |

Check each provider's documentation for its exact base URL and model names; they change. Whatever you use, the function you give a kit takes a prompt and returns text.

## 4. Run the council on real models

`examples/council_any_model.py` builds one brain per model and runs a deliberation with anonymous cross-review, one voice per model family, and dissent carried. Try it without any model first:

```powershell
python examples\council_any_model.py --demo
```

Edit the two `make_asker(...)` lines to use your models, give brains from the same provider the same `family` name so they count once, and run it without `--demo`. The outcome is `CONSENSUS`, `CONSENSUS_WITH_DISSENT`, `CONSENSUS_SEVERAL`, `SPLIT` or `INSUFFICIENT`, and the chain records hashes only.

## 5. Put a gate in front of an agent CLI

Agent command-line tools run shell commands and edit files. Two honest patterns exist today:

**A. A hook that denies by default.** Some agent CLIs run a command before each tool call and let it block the call. `examples/pretooluse_gate.py` is written for the form Claude Code's hooks take: the call arrives as JSON on standard input, exit code 2 blocks it, and the message on standard error goes back to the model. It allows only commands matching rules in `allow.json`, refuses anything with shell metacharacters, fails closed if it cannot read its input, and logs hashes of each decision. In Claude Code's settings you register it like this (check the current hooks documentation for the exact format):

```json
{ "hooks": { "PreToolUse": [ { "matcher": "Bash", "hooks": [ { "type": "command", "command": "python /full/path/to/pretooluse_gate.py" } ] } ] } }
```

**B. A wrapper command.** For tools without hooks, give the agent a wrapper as its only way to run commands. The wrapper asks a person for approval, runs the command only if approved, and records it, which is exactly what the terminal and two-gate kits do.

Other agent CLIs (Gemini CLI, Codex CLI and similar) have their own approval settings and extension points. This repository ships no ready-made integration for them; use pattern A or B and check each tool's documentation.

A real gate would require a human-signed, single-use commitment for anything outside the allow-list. See `vega-governance-jacket-sdk` for the commitment and the gate.

## 6. Keys and secrets

- Keep keys out of prompts, repos and chat. Use an operating-system vault or environment variables you set per session.
- A model that holds a key can leak it. The point of the family is that the model never holds authority; give it requests, not credentials.
- The pattern of an encrypted key card and a broker that makes the call on a model's behalf is being prepared as its own kit and is not published yet.

## 7. Limits

- The kits are reference implementations. They have not had an independent security review, and the cryptography has not had an expert review.
- A gate protects only the paths that go through it. An agent with an open shell has a side door.
- Approvals are only as good as the person giving them.
- Nothing here is legal advice. See the LICENSE in each repository.
