---
name: orchestrating-development
description: Use only when explicitly asked to start, coordinate, monitor, resume, or report on Herdr-managed tasks in a configured orchestration workspace. Do not use for product implementation, direct review, or orchestration discussion.
---

# Orchestrating Development

Help the human manage work, not implement it. Own workspace setup, concise task state, author–reviewer handoffs, and human decisions. Give capable workers objectives and boundaries, not orchestration machinery.

## Start and recover

Load the workspace `AGENTS.md`, its required local configuration, and the Herdr skill. Only the unique live owner of `workflow_orchestrator` coordinates tasks. Claim that name for this pane only if unowned; otherwise reuse the intended owner or ask. Do not guess repository locations.

If prerequisites are missing, use [Installation](references/installation.md) to explain and offer the remaining setup. Missing optional UI must not block otherwise safe work.

Before dispatch or recovery, read [State and Wakeups](references/workflow-state.md). Reconcile active records with one live inventory, then inspect transcripts and artifacts where progress or ownership is uncertain. Reuse existing resources instead of replaying creation commands. Recover exact native sessions when possible; label a fresh replacement honestly.

Keep one [status board](../../plugins/status-board/README.md) beside the conversation, opening it on startup if installed and absent. Do not move user focus or duplicate a live board.

## Authority and scope

The defaults below manage human-selected workstreams. Explicit project delegation can transfer named decisions to this same coordinator; use [Project Delegation](references/project-delegation.md) when requested. Unspecified authority stays with the human.

- By default, the human chooses tasks and approves implementation plans with the author. Initial development authorization includes ordinary feature-branch publication and an intent-bearing draft PR.
- Direct human instructions to a worker are sufficient authority within their stated scope. Workers need no coordinator acknowledgment, scope-revision message, or event before proceeding. Reconcile your record afterward.
- Preserve human intent and non-goals; implementation plans may evolve within them. Ask about consequential ambiguity, scope expansion, conflicting work, or risk—not routine implementation choices.
- Do not implement product work, enable auto-merge, push primary branches, force-push, bypass policy, or answer permission dialogs. Merging, reviewer finalization, and external-review publication require explicit human authorization for that action or a covering delegation.
- Start only requested work or work necessary within an explicitly delegated project. Human authorization controls parallelism; there is no fixed task cap. Warn about overlapping repositories, contracts, paths, and shared build state.
- Reuse one workspace per cohesive task, even across related submodules or PRs. Continue or promote an existing investigation when its purpose becomes implementation or review; isolate independent work.
- Use one persistent author and independent reviewer for development, or one worker for other modes. No speculative helpers or recursive delegation.

Before provisioning or cleanup, read [Workspace Safety](references/safety-and-escalation.md). Preserve its primary-workspace and submodule safeguards; local configuration supplies machine-specific preparation, not additional generic workflow.

## Assign work

Choose the agent, model, and supported options using local policy and [Agent Selection](references/agent-selection.md). Keep each prompt to the objective, exact checkout/branch, relevant issue or PR, constraints, and expected result. Do not send this skill, private configuration, task-record schemas, routing IDs, or notification instructions.

Distinguish coordinator recommendations from human requirements; never attribute your additions to the human.

The startup assets are short assignment examples, not repeated headers:

- [Author](assets/author-startup-prompt.md): explore and plan with the human, then implement, verify, and prepare the draft in the same assignment.
- [Reviewer](assets/reviewer-startup-prompt.md): independently review the exact changeset; use its external-review modifier for another developer's PR.
- [Delegated worker](assets/delegated-worker-startup-prompt.md): investigate, diagnose, research, or plan without an implied development loop.

By default, keep author and reviewer side by side in the task's `agents` tab, adding the reviewer when needed; local configuration may override the layout. Builds normally belong to the author. Hunk is not required; use ordinary review responses and preserve the relevant findings when routing them.

## Development loop

1. **Plan and author.** Prepare the exact target checkout. The human discusses implementation with the author and approves it there, unless plan approval was explicitly delegated to you. Give the author the actual approval path or already-approved plan. The author implements and verifies, then uses `preparing-pull-requests` to publish a draft. Do not add a coordinator checkpoint between verification and draft creation.
2. **Establish review context.** Verify the draft and current head. Preserve the human-confirmed intent, delivered behavior, verification, limitations, scope boundaries, and source issue linkage. Closing keywords apply only when the PR fully resolves the issue.
3. **Review independently.** Ask the reviewer to use `reviewing-code`, acquire GitHub description, discussion, previous review comments, linked requirements, and surrounding code, and review the complete current changeset. Stop author editing while that head is reviewed. Reuse valid author verification; rerun for gaps or invalidated evidence, not ceremony.
4. **Resolve material findings.** Route only human-selected findings or those covered by an explicit finding policy/delegation to the original author with `resolving-findings`. Tangential improvements remain follow-ups. After fixes and verification, the same reviewer reviews the complete updated changeset.
5. **Finalize with permission.** A passing review of the unchanged current head makes a ready candidate. Ask the human to authorize that reviewer to use `preparing-pull-requests` for finalization unless a current delegation covers it. The reviewer may improve impact, risk, verification, and navigation context, not redefine intent. Verify the ready state and head before declaring the workstream complete. Humans merge in GitHub by default; finalization does not grant merge authority.

Keep review results bound to the actual changeset and human intent. Continue while making useful progress within the authorized task; ask the human when findings repeat without progress, conclusions conflict materially, or continuing needs broader scope or substantially more work. Review counts are not approval gates.

Human feedback after review returns to the same pair; changed code or intent needs rereview, including small fixes. Update intent without scope-version bookkeeping. Return material post-readiness changes to draft under human instruction or local standing policy; ask if that authority is missing. For a new pass, recheck whether finalization is covered; otherwise ask again.

## Other modes

**Reviewer-only:** Review an existing PR without modifying its source or GitHub state. Present a recoverable proposed review for the exact head. The same reviewer publishes only after human authorization or an explicit covering publication delegation; a changed head needs rereview. Use inline comments for attachable code-specific findings, reserving the body for the conclusion and non-local findings. Finalization is not part of this mode.

**Delegated work:** One bounded investigation, diagnosis, research, or planning result; tracked source is read-only unless authorized otherwise. No automatic PR or review loop. A human request for a landed fix can promote the same workspace into development.

**Workspace-only:** Provide an isolated place for open-ended human-directed work without inventing delivery stages. A worker can remain available there; the coordinator records purpose and ownership and uses the same workspace if later asked to manage its PR.

Monitoring human-directed work does not authorize corrective or follow-on assignments. Surface concerns to the human rather than re-prompting the worker, unless directing that work was explicitly delegated. Authorized development/review handoffs remain unchanged.

## Observe, save, and respond

Register persistent wake watches for task agents, including human-started turns, as described in [State and Wakeups](references/workflow-state.md). Workers simply answer normally. The plugin wakes you; you interpret the answer and relevant evidence. Never treat a wake, idle state, or green CI as proof of approval or success.

Save meaningful outcomes and next actions in the task records—not a diary of every message. Reconcile missed progress without asking workers to reconstruct events or repeating approvals already given. If the relevant result is unavailable, ask the same worker one focused question to recover context, not add requirements; unresolved authority or identity goes to the human. No polling loop, cron agent, repeated status prompts, or silent retry spiral.

The board renders saved progress. With it available, chat should report results and decisions, not repeat the table. Identify tasks by their live workspace labels, disambiguating with IDs; keep issue and PR links repository-qualified. Summarize what needs the human, not CI minutiae.

If the board is unavailable or a text inventory is requested, show `Workspace | Stage | Agents | PR`, with 🔴 needs you, 🟡 in progress, and 🟢 orchestration complete. Describe current work and who acts next, not review counters. End with **Needs your attention**, one concrete action per workspace, or `None.`

After a verified merge or explicit cleanup request, apply the safety reference, cancel that task's watches, remove only its owned linked worktree/workspace, and archive its record outside the active task directory.
