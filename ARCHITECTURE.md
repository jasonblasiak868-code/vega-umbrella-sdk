# vega-umbrella-sdk — Architecture

**Contents:** [Layer map](#where-it-sits) · [Components](#components) · [Assembly workflow](#assembly-workflow-and-where-it-fails-closed) · [Approval workflow](#approval-workflow-and-where-it-fails-closed) · [Audit workflow](#audit-workflow) · [Custom constraints](#custom-constraints)

## Where it sits

Layer 15, assemble, the top of the stack. The whole map is in [ORGANISM.md](ORGANISM.md).

```mermaid
flowchart TB
    U[15 assemble: umbrella - THIS REPO] --> K[All lower kits, imported only when a lane asks]
    U --> C[0 record: custody - chains and ledger]
    H[The human] -->|signs in their own terminal| U
```

## Components

| Module | Concern | Uses |
|---|---|---|
| `registry` | Who owns what, layers, order | none |
| `organism` | One key, one ledger, one gate, lanes, anchor | custody; other kits lazily |
| `audit` | Read-only pre-deploy check | registry, custody `safepaths` |
| `feedback` | Feedback draft | registry names |
| `__main__` | Command line | registry, audit |

## Assembly workflow and where it fails closed

```mermaid
flowchart TD
    R[Load FAMILY] --> CR{check_registry passes}
    CR -->|no| X1[RegistryRefused]
    CR -->|yes| OG[Organism built with the human public key]
    OG --> LN{lane name valid}
    LN -->|no| X2[OrganismRefused]
    LN -->|yes| IM{kit for this lane importable}
    IM -->|no| X3[OrganismRefused names the missing module]
    IM -->|yes| CH[custody chain for the lane]
    CH --> AN[anchor records every lane head]
    AN --> VA{verify_all: every chain intact}
    VA -->|no| X4[tamper reported]
```

| Stop point | Mechanism | Where |
|---|---|---|
| Unsound registry | raise | `registry.check_registry` |
| Bad lane name | raise | `organism.Organism.lane` |
| Missing kit | raise on request | `organism._need` |
| Broken chain | reported by `verify_all` | `organism.Organism.verify_all` |

## Approval workflow and where it fails closed

```mermaid
flowchart TD
    S[Human signs action and parameters in their own terminal] --> P[present: look without spending]
    P --> CAP{within per-key and total caps}
    CAP -->|no| X1[refused]
    CAP -->|yes| Q[pending, keyed by exact action and params]
    Q --> T[take: run the exit gate]
    T --> OK{valid, unexpired, exact match, unused}
    OK -->|no| X2[refused]
    OK -->|yes| B[signature burned, action may proceed]
```

| Stop point | Mechanism | Where |
|---|---|---|
| Unsigned or foreign-signed commitment | keyed ledger refuses | `Organism` |
| Reuse or wrong action | exit gate refuses | `Approvals.take` |
| Flooding pending approvals | caps | `PRESENT_CAP`, `PER_KEY_CAP` |

## Audit workflow

```mermaid
flowchart LR
    RT[root folder] --> A[audit_family reads, never writes]
    A --> C1[registry sound]
    A --> C2[each BUILT kit on disk with dependencies]
    A --> C3[licence hash matches]
    A --> C4[review has no high or medium finding]
    A --> C5[tests ran and passed]
    A --> C6[release blocks reported]
    C1 --> V{all clear}
    C2 --> V
    C3 --> V
    C4 --> V
    C5 --> V
    C6 --> V
    V -->|yes| RD[READY]
    V -->|no| BL[BLOCKED with reasons]
```

## Custom constraints

Extension points in the published code: new registry entries (each must claim an unowned concern and depend only on lower layers) and the lanes registered with the Organism. User-defined constraints may be STRICTER than the legal minimum for the applicable jurisdiction, never looser. Jurisdictional legal minimums are defined by the jurisdiction registry (vega-jurisdiction-sdk); a custom constraint that would drop below a registered minimum is rejected at the gate.
