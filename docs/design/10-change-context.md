# Change Context

## Artifact Overview

Change context preserves the intent needed to carry one cohesive change through the [development workflow](./01-workflow-overview.md), including recovery after an interrupted or transferred session. It separates the authoritative change brief from an optional implementation plan and from the review context assembled for downstream evaluation.

This separation allows implementation tactics to evolve without silently changing the accepted outcome. Before a draft pull request exists, the context must have a recoverable local representation; afterward, the pull-request description becomes the durable team-facing statement of intent while local artifacts may continue to provide additional working detail.

## Context Artifacts

### Change Brief

The change brief is the authoritative statement of intended outcome. Its depth is proportional to the change, but it must identify:

- the problem or goal;
- observable acceptance criteria;
- relevant constraints and non-goals;
- known gaps or unresolved decisions;
- its source and most recent confirmation; and
- the repository and changeset to which it applies.

The brief describes required results rather than freezing an implementation approach. Only the developer may authorize a material change to its intent or scope.

### Implementation Plan

The implementation plan is optional working guidance for the [author](./20-authoring.md). It may describe an approach, tasks, affected areas, and expected verification, but it is not itself an acceptance contract. The author may refine it as repository evidence changes the best approach, provided the change brief remains satisfied and scope is not silently broadened.

The plan may remain local and uncommitted. If it contains information required to understand or review the final change, that information must be promoted into the change brief or pull-request description before handoff.

### Review Context

Review context is a derived, provenance-aware snapshot supplied to the [reviewer](./30-reviewing-code.md). It combines the current change brief with the complete changeset identity, relevant repository guidance, pull-request claims, verification evidence, and any unresolved prior findings.

Review context does not replace its sources or make inferred intent authoritative. Each review must be able to distinguish developer-confirmed criteria from context reconstructed from code, history, or agent transcripts.

## Responsibilities and Boundaries

- The **developer** confirms the initial brief and authorizes subsequent changes to intent or scope.
- The **author** keeps working context current and records discoveries that affect the accepted outcome.
- The **reviewer** evaluates the changeset against confirmed intent and reports when intent is absent, ambiguous, or stale.
- The **pull-request lifecycle** promotes stable context into the durable team-facing record as defined in [`50-pull-request-lifecycle.md`](./50-pull-request-lifecycle.md).
- Review surfaces such as Hunk may display context, but they do not own it; transport behavior belongs to [`60-review-adapters.md`](./60-review-adapters.md).

Change context is not a product specification system, permanent task tracker, raw conversation archive, or substitute for repository documentation that the delivered behavior makes necessary.

## Inputs and Outputs

Inputs may include direct developer instructions, an existing issue or pull-request description, repository documentation, and explicitly selected prior discussion. Code and commit history provide evidence about implementation but cannot establish unstated intent by themselves.

The artifact contract produces:

- an authoritative change brief available to author and reviewer;
- an optional implementation plan available to the author;
- a review-context snapshot bound to the reviewed changeset; and
- team-facing intent suitable for the draft pull-request description.

## Lifecycle and Recovery

1. **Establish:** Capture a minimal brief before implementation begins.
2. **Plan:** Add implementation guidance only when the change benefits from it.
3. **Maintain:** Record discoveries and obtain developer approval when they alter intent or scope.
4. **Publish:** Use the pull-request preparation contract in [`55-preparing-pull-requests.md`](./55-preparing-pull-requests.md) to promote the confirmed brief into the structured draft description.
5. **Review:** Assemble a fresh review context for the current changeset.
6. **Finalize:** Update the durable pull-request record with the actual delivered behavior and accepted limitations.

Before a draft pull request exists, context must survive loss of an agent session and must remain associated with the correct repository and branch. The exact local storage mechanism remains open; relying only on chat history or an agent's memory is insufficient.

When taking over incomplete work, recovery uses the strongest available sources in this order: current developer confirmation, the current pull-request description and linked requirements, an explicit saved brief, and clearly attributed historical discussion. Inferred intent must be labeled and presented for confirmation when it could affect correctness or scope.

## Stale-Context Handling

Context must carry enough identity to detect a mismatch with the current repository, branch, base, or reviewed changeset. A consumer must refresh or reconfirm context when the association cannot be established, the diff has materially changed, or authoritative sources disagree.

Stale context may inform investigation but must not silently govern implementation or review. The current code also does not override confirmed acceptance criteria merely because it is newer.

## Open Questions

The following choices remain intentionally unresolved and are tracked in [`90-decisions-and-open-questions.md`](./90-decisions-and-open-questions.md):

- the local pre-pull-request storage mechanism and retention policy;
- the minimum template for very small changes;
- synchronization between local context and an edited pull-request description; and
- changeset identity across worktrees, submodules, and meta-repositories.

The initial implementation of this contract is a concise, reusable change-brief template. It is not a standalone skill; the separate pull-request preparation skill consumes the brief when creating the durable GitHub handoff. A future helper may assist with drafting the brief only if repeated use demonstrates that a specialized skill adds value.
