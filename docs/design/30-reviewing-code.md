# Reviewing Code

## Skill Contract Overview

The reviewing-code skill performs an independent technical assessment of an identified changeset. It determines whether the change safely and maintainably delivers its stated intent, produces evidence-backed findings, and recommends whether the changeset is ready to leave the private review loop.

The skill owns review judgment only. It does not edit code, select work for the author, publish feedback, or change pull-request state. Those responsibilities belong to [finding resolution](./40-resolving-findings.md), [review adapters](./60-review-adapters.md), and the [pull-request lifecycle](./50-pull-request-lifecycle.md).

## Explicit Trigger

The skill activates only when the developer explicitly requests a formal review of a pull request, branch, commit range, or working-tree changeset, or invokes the skill by name. The request may identify a GitHub pull request or a local changeset; the review procedure is the same after context is acquired.

The reviewer role is normally assigned once in a separate persistent session. Subsequent explicit rereview requests reactivate the skill in that same session as described in [`05-human-workflow.md`](./05-human-workflow.md); role continuity alone does not cause background review.

The skill must not activate merely because an agent is:

- implementing or explaining code;
- inspecting a diff for status or handoff purposes;
- performing ordinary self-verification during authoring;
- resolving previously selected review findings; or
- asked a narrow question about one code fragment without a formal review request.

When the target or base is not explicit, the reviewer should derive it from reliable repository or pull-request state when possible. It asks the developer only when ambiguity could materially change the reviewed changeset.

## Inputs and Review Identity

The reviewer establishes a review context from:

- the exact base and head revisions or equivalent working-tree state;
- the current change brief or pull-request description;
- applicable repository instructions and architectural documentation;
- linked requirements when they are part of the stated intent;
- the complete diff and directly affected neighboring code; and
- available verification evidence and unresolved findings from prior rounds.

The review is bound to the identified changeset. If the code changes materially during analysis, the reviewer refreshes the affected analysis or restarts the review rather than presenting stale conclusions. Missing or inferred intent is labeled according to the [change-context contract](./10-change-context.md); an inferred plan is never treated as a confirmed requirement.

## Adaptive Phased Review

The reviewer uses distinct reasoning phases to protect depth on substantial changes:

0. **Orientation and intent:** establish domain, scope, blast radius, requirements, and architectural placement.
1. **Architecture and integration:** examine interfaces, compatibility, dependencies, layering, deployment, and cross-component effects.
2. **Behavior and safety:** trace control flow, state, failure paths, boundaries, concurrency, resources, and domain invariants.
3. **Maintainability and verification:** assess abstractions, clarity, tests, documentation, omissions, and operational evidence.
4. **Synthesis:** validate, deduplicate, prioritize, and present the findings as one coherent review.

Phase 0 establishes the high-level interpretation and highest-leverage concerns; it is not expected to find every defect. The later phases are independent passes specifically intended to catch integration, correctness, safety, maintainability, and verification issues that the initial architectural pass may miss.

Each phase is performed as an independent analytical pass, but phases do not require developer approval between them. An observation discovered early may be placed in a candidate ledger and validated during the phase that owns it. This preserves coherent senior-engineering reasoning without allowing one early impression to replace focused analysis.

Checks are applicability prompts, not a mandatory quota. The reviewer records why a whole phase or major concern is inapplicable when that decision is not obvious. A comment-only change may need only intent, accuracy, and consistency review; a concurrency or public-interface change warrants deeper passes. Change size influences review strategy and context management but is never an automatic rejection threshold.

Adaptive depth does not eliminate the correctness pass. Every behavior-changing change receives focused tracing of the changed behavior, affected callers and contracts, input and output boundaries, important failure paths, state or resource lifecycle, and whether tests exercise the relevant behavior. Domain-specific safety concerns expand this minimum when applicable. Documentation-only and similarly non-executable changes may omit concerns that genuinely cannot apply.

## Broad Analysis and Strict Output

The reviewer separates investigation breadth from the output threshold. It may inspect many concerns and retain multiple candidates internally while surfacing only findings that survive validation and materially affect the current change or require a developer decision.

This distinction prevents two opposite failures:

- suppressing investigation early in the name of a quiet review can miss real defects; and
- surfacing every technically valid observation can bury material findings and inflate the pull request.

The final review is intentionally sparse. Preference-only alternatives, theoretical hardening, automated style concerns, and negligible-impact observations are omitted rather than labeled as optional work. Repeated instances of one material pattern become one representative finding with the affected scope described.

The skill uses a concise professional disposition rather than a reviewer persona or stylized voice. Findings should be direct, neutral, and evidence-based. Tone must not introduce praise quotas, performative severity, or extra prose that competes with the technical result.

The reviewer pauses only when progress requires a developer decision, such as irreconcilable intent, an uncertain target, a fundamental scope problem, or authorization for costly or state-changing verification.

## Evidence and Review Judgment

Findings must be grounded in inspected code, reproducible behavior, violated contracts, or a credible traced failure scenario. Reproduction strengthens evidence but is not mandatory when the environment cannot exercise the path safely or economically; the reviewer states the remaining uncertainty instead of suppressing a material concern. The reviewer explores callers, consumers, tests, and relevant history as needed rather than judging the diff in isolation. It may run proportionate repository-approved builds and tests within the authorized environment, but it does not modify source code to prove or repair a finding.

Passing tests and CI are evidence, not substitutes for review. The reviewer checks whether available verification actually exercises the changed contract and important failure paths without manually duplicating checks that already provide adequate coverage.

The reviewer distinguishes defects from preferences. It does not request speculative flexibility, unrelated cleanup, or broad redesign merely because a different implementation is possible. New abstractions must earn their complexity, but established local conventions and the cohesive change boundary also carry weight.

## Finding Contract

Each actionable finding contains:

- a stable identifier and concise title;
- an exact location when one exists;
- the observed behavior or condition;
- the concrete consequence and affected scenario;
- supporting evidence and relevant uncertainty;
- the smallest credible direction for resolution; and
- classifications for severity, current-change relevance, and resolution risk.

**Severity** expresses impact on correctness, safety, security, compatibility, operability, or maintainability. **Current-change relevance** distinguishes required in-scope work from questions and follow-up candidates. **Resolution risk** indicates whether a fix appears routine and local or requires product, architectural, or scope judgment.

These classifications inform developer disposition but do not authorize edits. In particular, a valid tangential concern remains a follow-up candidate and must not be converted into current pull-request work by the reviewer or author.

Non-actionable observations are omitted unless they materially clarify risk or reviewer guidance. Positive observations may appear in the summary when they explain why a risky area is acceptable, but the output is not an audit log of every check performed.

## Output and Recommendation

The review output is medium-independent and contains:

- the reviewed changeset identity and understood intent;
- a concise risk and impact summary;
- actionable findings in priority order;
- follow-up candidates kept separate from current-change findings;
- verification performed and material evidence not obtained;
- assumptions, limitations, and unresolved questions; and
- one recommendation: **changes required**, **developer decision required**, or **ready candidate**.

A **ready candidate** recommendation means no known material in-scope defect remains after the completed review. The bar is not perfection, but neither is aggregate “net improvement” sufficient when the change introduces a material regression. A ready-candidate result does not mark the pull request ready, approve it on GitHub, or authorize merge. Hunk and GitHub translate the same review result through the contracts in [`60-review-adapters.md`](./60-review-adapters.md).

## Rereview Contract

After fixes, the same reviewer normally examines the complete current changeset rather than checking only whether prior comments were edited. It revalidates previous findings, looks for regressions and scope growth, refreshes risk and verification conclusions, and issues a new recommendation bound to the new head state.

Reviewer independence comes from remaining separate from the author, not from discarding the reviewer session after every pass. Retaining the reviewer preserves repository discovery and review history, while a full base-to-head rereview prevents memory of earlier findings from narrowing the analysis. A replacement reviewer is appropriate when the session is lost, its context is unreliable, scope has materially changed, or the reviewer has participated in implementation.

## Skill Packaging Boundary

The eventual skill should use progressive disclosure:

- its main instructions own explicit triggering, context acquisition, phase routing, pause conditions, and final synthesis;
- phase references contain detailed concern prompts and are loaded only when applicable;
- a shared finding template defines medium-independent output; and
- Hunk and GitHub mechanics remain outside the analytical core.

The package must not recreate the entire workflow specification, require a repository tracking file, or hard-code one hosting service, build system, language, or line-count limit.

## Boundaries

The reviewer does not:

- modify source code or act as the author;
- decide which non-blocking findings the developer must accept;
- create issues or expand the pull-request scope;
- publish comments or reviews without developer authorization;
- update the pull-request description or readiness state except through [`55-preparing-pull-requests.md`](./55-preparing-pull-requests.md) after a successful final review and separate authorization;
- treat CI success as proof of correctness; or
- merge or bypass repository policy.
