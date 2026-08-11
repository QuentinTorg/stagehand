# Managed Agent Contracts

## General contract

A development task has one persistent author and one persistent independent reviewer; reviewer-only work has one reviewer. Reuse roles across rounds. Do not add a fixer or replace a healthy role for a different answer.

Start each role with its template and a rendered managed workflow control block. Prepend a fresh block to every later handoff so identity, endpoint, scope, stage, and outcomes never depend on memory. Fill it from the validated record; never send orchestration instructions into product worktrees.

The block remains authoritative until explicit release or cleanup. Human discussion may grant a checkpoint but does not detach the role, change its endpoint, or waive its next event. Each role must:

- follow the target repository's instructions and applicable task-specific skills;
- remain within their assigned worktree and task;
- avoid spawning or delegating to other agents without explicit human authorization;
- send the required semantic events through the endpoint and delivery procedure in the current control block;
- stop rather than invent authority when scope, risk, permissions, or task identity is unclear.

## Signaling protocol

Send an allowed semantic event at each workflow boundary or diagnosed blocker, with fields verified from current state. Plan discussion and progress need no event. Follow the block's delivery and fallback procedure; fallback enables recovery, not advancement.

After proportionate diagnosis, authors report `needs-human` and reviewers `review-needs-human`, naming the operation, error or ambiguity, and required decision. Initialization, build, verification, GitHub, Hunk, finalization, and event failures do not create new event names.

## Author contract

The author startup prompt gives the desired outcome, not its implementation.

Before approval, the author may inspect and propose scope, implementation, and verification, but may not edit, commit, push, or create a PR. Approval must occur in that author session.

Before planning, verify the prepared target path, feature branch, and recorded base ancestry. On mismatch, diagnose and emit `needs-human`; do not branch from incidental state, repair orchestration setup, invent events, or stop silently.

After approval, deliver `implementation-started` before editing; failed delivery pauses for recovery. Send `implementation-ready` after implementation and verification. Only the orchestrator's later `drafting` handoff permits branch publication and initial draft creation; initial task authorization already covers it.

For GitHub tasks, link the supplied issue repository, number, and URL using repository conventions. Use a closing keyword only when the PR fully resolves it.

The same author resolves only selected findings, using the finding-resolution skill when instructed. It must consume Hunk comments before editing because reload may clear them.

Send `scope-revised` before implementing a human-directed material expansion. Intent-preserving plan refinement is not a revision.

For selected post-review feedback, send `post-review-changes-started` before editing. Small intent-preserving corrections follow finding resolution. Material revisions include a durable brief and wait for scope-version and draft-state handling. Both end with `fixes-ready` and complete rereview by the same reviewer.

## Reviewer contract

Start the reviewer only after validating `draft-pr-ready`, supplying the draft PR, linked issue, base, head, scope, round, and Hunk session.

The reviewer obtains intent from the GitHub PR description, comments, linked issue or requirements, current head, and available checks; inspects surrounding code; then performs the reviewing-code skill's complete phased review. Hunk delivers findings but neither defines intent nor replaces reasoning.

Record only material actionable findings in Hunk. Emit `review-findings`, `review-needs-human`, or `review-passed` as appropriate; passing never changes PR readiness.

The same reviewer completely rereviews base-to-head after every fix. New scope restarts at phase zero, not a delta review.

Only a finalization handoff with human authorization for the exact reviewed head permits the preparation skill, reviewer-owned context reconciliation, readiness change, and `pull-request-finalized`. Finalization excludes GitHub approval and merge unless separately requested; merge remains human-executed.

For material post-readiness feedback, explicit authority or standing policy may direct the reviewer to change only draft state and emit `pull-request-returned-to-draft`. It never implements, rewrites intent, replies, or resolves threads. A changed head requires complete rereview and new finalization authorization.

## Reviewer-only contract

The external reviewer receives the existing PR, exact base and head, checkout, round, and task-owned proposal path. It has no author, fixer, Hunk, draft creation, or finalization authority.

It performs the same complete review and context acquisition, writes without publishing a proposed GitHub review, then emits `review-proposed` with exact head, conclusion, and recoverable proposal.

Only explicit authorization for the unchanged proposal and head permits publication by that reviewer. Preserve its conclusion and material content, then emit `review-published`. Never modify source, branch, description, labels, draft/readiness, or merge state. A changed head requires a new complete review.

## Replacement

Replace a role only when its process or session is lost, its context is unreliable, it participated in the incompatible role, or the human directs replacement. Before starting the replacement, verify the old process is no longer active or obtain human authority to stop it. Record the replacement agent name and give it durable task, PR, changeset, verification, and unresolved-finding context.
