# Managed Agent Contracts

## General contract

A development task has one persistent author and one persistent independent reviewer; reviewer-only work has one reviewer; delegated work has one worker. Reuse roles across rounds. Do not add helpers or replace a healthy role for a different answer.

Start each role with its template and a rendered managed workflow control block. Later handoffs need only the compact block plus the new outcome, boundaries, and evidence requirement; do not restate the task history or teach capable agents how to perform ordinary engineering work. Fill identities from the validated record; never send orchestration internals into product worktrees.

The block remains authoritative until explicit release or cleanup. Human discussion may grant a supervised checkpoint but does not detach the role, change its endpoint, or waive its next event. In autonomous-project mode, only the named orchestrator approval actor may advance a package plan. Each role must:

- follow the target repository's instructions and applicable task-specific skills;
- remain within their assigned worktree and task;
- never spawn or delegate to other agents in a managed task;
- treat project, package, authoritative source sections, reservations, approval actor, and integration branch as literal boundaries;
- never implement on, commit to, push to, or merge into `main`; in autonomous-project mode, never target a pull request at `main`;
- never run `git push` or mutating `gh` commands directly; when publication is authorized, use only the configured record-aware guard for the exact task branch and head and, when separately authorized, its initial-draft operation, never the integration branch;
- never invoke privilege escalation, enter credentials, or mutate host network/system configuration; privileged scenarios may be authored only as unexecuted human-gated evidence;
- send the required semantic events through the endpoint and delivery procedure in the current control block;
- use engineering judgment to resolve ordinary repository state, missing optional CI, dependency initialization, tool-version differences, build failures, and verification setup inside the assigned scope;
- stop only when progress needs authority or essential information outside the task contract.

## Signaling protocol

Send an allowed semantic event at each workflow boundary or diagnosed blocker, with fields verified from current state. Plan discussion and progress need no event. Follow the block's delivery and fallback procedure; fallback enables recovery, not advancement.

After proportionate diagnosis, authors and workers report `needs-human`; reviewers report `review-needs-human`. Use these only when no safe in-scope recovery remains. A failed command, absent non-required CI, uninitialized dependency, sandbox retry, or tool-output variation is normally a problem to solve, not a human decision.

## Author contract

The author startup prompt gives the desired outcome, not its implementation.

Before approval, the author may inspect and propose scope, implementation, and verification, but may not edit, commit, push, or create a PR. Supervised approval occurs in the author session. Autonomous-project approval occurs when the orchestrator validates `plan-proposed` against the cited source documents and returns a fresh implementation control block.

Autonomous plan validation covers package objective, dependencies, reserved ownership, neighbor contracts, exclusions, abstraction placement, reusable mocks/simulation, every required verification tier, and completion evidence. The orchestrator returns bounded corrections until these agree; it does not ask the human to perform routine plan approval.

Before planning, verify the prepared target path, feature branch, and recorded base ancestry. On mismatch, diagnose and emit `needs-human`; do not branch from incidental state, repair orchestration setup, invent events, or stop silently.

After approval, deliver `implementation-started` before editing; failed delivery pauses for recovery. Send `implementation-ready` after implementation and verification. Only the orchestrator's later `drafting` handoff permits branch publication and initial draft creation; initial task authorization already covers it.

For GitHub tasks, link the supplied issue repository, number, and URL using repository conventions. Use a closing keyword only when the PR fully resolves it.

The same author resolves only selected findings, using the finding-resolution skill when instructed. It must consume Hunk comments before editing because reload may clear them.

Direct human instructions in a supervised author pane are authoritative. In autonomous-project mode, scope and specification changes route through `project-decision-needed`; the orchestrator may authorize only changes inside the charter and must require the owning document and material ADR update. Intent-preserving plan refinement is not a revision.

For selected post-review feedback, send `post-review-changes-started` before editing. Small intent-preserving corrections follow finding resolution. Material revisions include a durable brief and wait for scope-version and draft-state handling. Both end with `fixes-ready` and complete rereview by the same reviewer.

## Reviewer contract

Start the reviewer only after validating `draft-pr-ready`, supplying the draft PR, linked issue, base, head, scope, round, and Hunk session.

The reviewer obtains intent from the GitHub PR description, comments, linked issue or requirements, authoritative source sections, related ADRs, package record, current head, and available checks; inspects surrounding code; then performs the reviewing-code skill's complete phased review. Hunk delivers findings but neither defines intent nor replaces reasoning.

For autonomous packages, review explicitly covers cohesive ownership, abstraction placement, dependency direction, maintainability, reusable mocks and simulation, every required verification tier, installability, deployment configuration, diagnostics, and agreement among documents, schemas, code, tests, and behavior. Reject speculative frameworks, duplicated contracts, cross-layer logic, bloat, and implementation-only specification changes.

Record only material actionable findings in Hunk. Emit `review-findings`, `review-needs-human`, or `review-passed` as appropriate; passing never changes PR readiness.

The same reviewer completely rereviews base-to-head after every fix. New scope restarts at phase zero, not a delta review.

Only a finalization handoff with authorization from the recorded approval actor for the exact reviewed head permits the preparation skill, reviewer-owned context reconciliation, readiness change, and `pull-request-finalized`. An active autonomous charter may supply that authorization. Finalization never includes merge. In supervised mode, a GitHub approval review requires a separate human request and merge remains human-executed. In autonomous-project mode, only the orchestrator's guarded squash procedure may merge into the recorded integration branch.

For material post-readiness feedback, explicit authority or standing policy may direct the reviewer to change only draft state and emit `pull-request-returned-to-draft`. It never implements, rewrites intent, replies, or resolves threads. A changed head requires complete rereview and new finalization authorization.

## Reviewer-only contract

The external reviewer receives the existing PR, exact base and head, checkout, round, and task-owned proposal path. It has no author, fixer, Hunk, draft creation, or finalization authority.

It performs the same complete review and context acquisition, writes without publishing a proposed GitHub review, then emits `review-proposed` with exact head, conclusion, and recoverable proposal.

Only explicit authorization for the unchanged proposal and head permits publication by that reviewer. Preserve its conclusion and material content, then emit `review-published`. Never modify source, branch, description, labels, draft/readiness, or merge state. A changed head requires a new complete review.

## Delegated worker contract

The worker performs the bounded objective under its recorded mutation boundary. Tracked source is read-only unless the human explicitly changes that boundary; work intended to land requires the development workflow. The worker creates no PR, review, or additional agent. It emits `work-complete` with a concise summary and optional durable `resultRef`, or `needs-human` after diagnosing a blocker.

## Replacement

Replace a role only when its process or session is lost, its context is unreliable, it participated in an incompatible role, the autonomous convergence procedure selects replacement, or the human directs replacement. First verify the old process stopped or obtain authority to stop it. Record the replacement and provide only its mode-relevant durable context.
