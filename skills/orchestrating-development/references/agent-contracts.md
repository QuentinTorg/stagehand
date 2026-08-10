# Managed Agent Contracts

## General contract

A development task receives one persistent author and, when review begins, one persistent independent reviewer. A reviewer-only task receives one persistent reviewer and no author. Reuse assigned roles across review rounds. Do not create a third fixer or replace a healthy role to obtain a different answer.

The orchestrator starts agents with the corresponding role template and prepends the rendered managed workflow control block. It prepends a fresh block again for every later handoff so task identity, role, endpoint, scope, recorded stage, and allowed outcomes do not depend on conversational memory. Fill every placeholder from the validated task record. Do not send the orchestration skill or personal orchestration-repository instructions into product worktrees.

The control block remains authoritative until the named orchestrator or human explicitly releases the role or the task is cleaned up. Direct human discussion can grant a documented human checkpoint, but it does not detach the role, change its endpoint, or waive its next semantic event. Both managed roles must:

- follow the target repository's instructions and applicable task-specific skills;
- remain within their assigned worktree and task;
- avoid spawning or delegating to other agents without explicit human authorization;
- send the required semantic events through the endpoint and delivery procedure in the current control block;
- stop rather than invent authority when scope, risk, permissions, or task identity is unclear.

## Signaling protocol

A semantic event is required when a role reaches a documented workflow boundary or cannot reach the expected boundary inside its current authority. Ordinary plan discussion and progress updates do not require events. The role chooses only an event allowed by its current control block, verifies every required field from current state, diagnoses failures before classifying them as blockers, and follows the block's delivery and fallback procedure. A fallback is durable evidence for recovery, not permission to enter the next stage.

If work cannot proceed after proportionate diagnosis, authors use `needs-human` and reviewers use `review-needs-human`. The reason identifies the failed operation, observed error or ambiguity, and the decision or authority needed. Initialization, build, verification, GitHub, Hunk, finalization, and event-preparation failures are instances of these documented blocker outcomes; they are not new event names.

## Author contract

Start the author with the author startup prompt asset loaded by the core workflow. The task brief tells the author what outcome is wanted, not how to implement it.

Before human approval, the author may inspect repository instructions, status, code, tests, history, and relevant documentation. It may propose scope, implementation, and verification. It must not edit files, create commits, push, or create a pull request until the human explicitly approves implementation in that author session.

The author receives an already prepared development target. Before planning, it verifies the target path, feature branch, and recorded base ancestry. If they disagree, it diagnoses and emits `needs-human` with the mismatch rather than silently branching from incidental checkout state, repairing orchestration setup, inventing `initialization-failed`, or merely mentioning the problem in prose.

After approval, the author must successfully deliver `implementation-started` before its first edit. A failed delivery fallback stops implementation until recovery. When implementation and verification are ready, it sends `implementation-ready` rather than publishing or starting review itself. Only a subsequent control-block handoff from the orchestrator permits it to use the preparing-pull-requests skill to publish the branch and create the initial draft. Initial task authorization includes this routine draft creation; no second human approval is required.

When the task came from GitHub, the author receives the issue repository, number, and URL. The draft must link that issue using repository conventions. Use a closing keyword only when the pull request is intended to resolve the issue completely; otherwise preserve the relationship without claiming automatic closure.

The same author resolves selected findings. It must consume the current Hunk comments before editing because the later Hunk reload may clear them. It loads the finding-resolution skill only when explicitly asked to modify the selected set.

When the human materially expands the task in the author session, the author sends `scope-revised` before treating the new requirement as ordinary implementation. Minor implementation-plan refinement that preserves the confirmed outcome is not a scope revision.

After a successful review or finalization, selected human feedback may arrive through Herdr or an identified GitHub review. The author sends `post-review-changes-started` before editing so the orchestrator invalidates stale review state. A small intent-preserving correction may proceed through the finding-resolution contract. A material revision includes a durable brief reference and waits for the orchestrator to advance the scope version and decide pull-request draft state before implementation. Both paths end with `fixes-ready` and a complete rereview by the same reviewer.

## Reviewer contract

Start the reviewer with the reviewer startup prompt asset loaded by the core workflow only after validating `draft-pr-ready`. The reviewer receives the draft pull request, linked issue when present, base, current head, scope version, review round, and Hunk session identity.

The reviewer must query GitHub for the pull-request description, comments, linked issue or requirements, current head, and available checks before forming its understanding of intent. It then inspects surrounding code and performs the complete phased review defined by the reviewing-code skill. Hunk is the private delivery surface; it is not the source of intent or a substitute for review reasoning.

The reviewer records only material actionable findings in Hunk. When changes are required it emits `review-findings`; when a decision blocks review it emits `review-needs-human`; and when the complete current-head review passes it emits `review-passed` without changing pull-request readiness.

Use the same reviewer for rereview, but require a complete current base-to-head review after every fix round. A new scope version restarts review at phase zero rather than performing a narrow delta check.

After `review-passed`, the orchestrator returns the readiness result to the human. Only a finalization handoff carrying explicit human authorization for that exact reviewed head allows the reviewer to use the preparing-pull-requests skill, reconcile reviewer-owned context, mark the pull request ready, and emit `pull-request-finalized`. Finalization does not include submitting a GitHub approval review or merging unless the human separately requests an allowed review publication; merge always remains human-executed.

When post-readiness feedback is material, the orchestrator may direct the reviewer to return the pull request to draft under explicit human authority or a configured standing policy. The reviewer changes only draft state and emits `pull-request-returned-to-draft`. It does not implement feedback, rewrite intent, reply to comments, or resolve threads. Any changed head requires a complete rereview and new finalization authorization.

## Reviewer-only contract

Start a reviewer-only task with the external reviewer startup prompt. It receives the existing pull request, exact base and head, repository checkout, review round, and a task-owned proposal path. It has no author, fixer, Hunk requirement, draft-creation transition, or pull-request finalization authority.

The reviewer performs the same complete phased inspection and GitHub-context acquisition as a development reviewer, but writes a proposed GitHub review without publishing it. Its `review-proposed` event identifies the exact head, conclusion, and recoverable proposal. The orchestrator presents that proposal to the human.

Only explicit human authorization for the unchanged proposal and head permits the same reviewer to publish it. Publication must preserve the authorized conclusion and material content. The reviewer emits `review-published` afterward. It never modifies source, the pull-request branch, description, labels, draft state, readiness, or merge state. A changed head invalidates the proposal and requires a complete rereview.

## Replacement

Replace a role only when its process or session is lost, its context is unreliable, it participated in the incompatible role, or the human directs replacement. Before starting the replacement, verify the old process is no longer active or obtain human authority to stop it. Record the replacement agent name and give it durable task, PR, changeset, verification, and unresolved-finding context.
