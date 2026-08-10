# Authoring

## Workflow Contract Overview

Authoring turns an approved [change context](./10-change-context.md) into one cohesive, verified changeset and a draft pull request ready for independent review. The author owns implementation decisions within the authorized scope, gathers evidence appropriate to the change, and leaves enough current context for another agent or the developer to take over without relying on hidden conversation history.

Initial authoring ends at review handoff, but the author remains the implementation agent throughout the private review loop. It resumes work only for findings selected by the developer, then returns the updated changeset to the same reviewer. The author does not judge its own readiness or own pull-request finalization; those boundaries follow the [development workflow](./01-workflow-overview.md).

This contract does not require an authoring skill. In the initial implementation, the author is an ordinary coding agent controlled by the target repository's instructions, the developer-approved change brief, and any optional implementation plan. At explicit transitions, the same session loads the pull-request preparation skill to create the draft or the finding-resolution skill to address selected feedback. This document defines expected outcomes and handoff boundaries for the workflow; it need not be loaded into every authoring session when those controls already express the applicable requirements.

## Responsibilities and Inputs

The author receives:

- a developer-confirmed change brief and any optional implementation plan;
- the target repository, base, and feature branch;
- repository instructions and relevant architecture or product documentation;
- existing working-tree state that must be preserved; and
- known build, test, environment, and publication constraints.

Before editing, the author confirms that the brief applies to the current checkout, inspects repository status, identifies applicable instructions, and understands the affected interfaces. Missing context is recovered or escalated according to [`10-change-context.md`](./10-change-context.md) rather than guessed.

The author is responsible for implementing the accepted outcome, maintaining working context, verifying the result, and preparing an accurate review handoff. Repository evidence may change the implementation plan, but only the developer may authorize a material change to intent or scope.

## Scope Control

- Work must remain on a feature branch and must never be pushed directly to `main`.
- Unrelated pre-existing changes, commits, build artifacts, and submodule state must be preserved.
- New abstractions and dependencies must solve a present requirement and earn their maintenance cost.
- A discovered defect may be fixed in the current changeset only when the fix is necessary for the accepted outcome and remains small, local, and low risk.
- Tangential cleanup, speculative flexibility, and unrelated defects are recorded for developer disposition rather than absorbed into the pull request.
- Any discovery that changes product behavior, public contracts, architecture, compatibility, or the cohesive pull-request boundary requires developer approval.

When a required fix reveals that the original scope is no longer cohesive, the author pauses instead of disguising a second feature as implementation detail.

## Implementation Standards

The implementation must favor robust, maintainable abstractions over expedient patches. It must handle realistic boundary and failure cases, preserve existing documented intent, and update intent comments when behavior changes. New comments should explain architectural purpose or non-obvious constraints rather than narrating the code.

The author must use language and framework guarantees idiomatically. Compiler warnings, type safety, validation boundaries, and ownership rules are resolved at their cause rather than suppressed or bypassed.

## Verification and Evidence

Verification depth is proportional to risk and must demonstrate the accepted behavior rather than merely show that commands executed. Applicable evidence may include:

- focused unit or regression tests;
- integration, protocol, hardware, or simulation checks;
- compilation and static analysis;
- local or containerized execution; and
- manual evidence when behavior cannot be asserted automatically.

A bug fix normally includes evidence that fails without the fix. A behavior change exercises its acceptance criteria and important failure paths. Repository-configured build, test, formatting, and lint commands remain authoritative when applicable.

The author records exact checks, outcomes, relevant artifacts, and material limitations. Expensive builds may proceed from focused feedback to broader required validation, but anticipated CI does not excuse missing local evidence that is practical and necessary.

C++ build directories and other mutable caches are treated as checkout-specific unless the build system explicitly guarantees safe sharing. Docker, submodule, and meta-repository verification must record the revisions and repository layer actually tested; a clean parent diff alone does not prove that changed submodule code was validated.

## Draft Pull Request and Review Handoff

After implementation and appropriate verification, the developer explicitly asks the author to create a draft pull request. The author follows [`55-preparing-pull-requests.md`](./55-preparing-pull-requests.md) to publish only the cohesive feature branch and create the structured draft under the authorization model in [`50-pull-request-lifecycle.md`](./50-pull-request-lifecycle.md). Intermediate commits may remain iterative because the completed pull request is expected to be squash-merged.

The handoff provides the reviewer with:

- the draft pull request and complete base-to-head changeset;
- the current change brief and clearly identified inferred context;
- a concise implementation summary;
- verification commands, results, and artifacts;
- known limitations, open decisions, and scope exclusions;
- relevant submodule or meta-repository revisions; and
- any preserved unrelated workspace state the reviewer must avoid.

The author does not pre-approve its design, filter likely review findings, or frame uncertainty as success. Review behavior and output are owned by [`30-reviewing-code.md`](./30-reviewing-code.md).

## Interrupted-Work Recovery

Authoring must remain recoverable after loss of an agent session. The feature branch, saved change context, current repository state, and draft pull request when present are the recovery sources; an old transcript may supplement but not replace them.

A replacement author first inspects the current checkout and remote pull request, reconciles them with the confirmed brief, and identifies incomplete or unverified work. It must not continue from an obsolete plan merely because that plan is available.

## Completion Criteria and Boundaries

Authoring is complete when the intended change and all selected in-scope fixes are implemented on a feature branch, proportionate verification evidence is recorded, durable context reflects the current outcome, and the changeset has been returned for independent review.

Authoring does not:

- declare the changeset reviewed or ready to merge;
- resolve findings that the developer has not selected for the current pull request;
- mark the pull request ready for team review;
- merge, modify company policy, or bypass CI; or
- begin another feature automatically.

Unresolved details about worktree build isolation, long-running verification, and multi-repository changes are tracked in [`90-decisions-and-open-questions.md`](./90-decisions-and-open-questions.md).
