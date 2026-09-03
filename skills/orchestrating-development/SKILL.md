---
name: orchestrating-development
description: Use when the user explicitly asks the controller in a configured Stagehand workspace to start, coordinate, pause, resume, monitor, or report on Herdr-managed delivery tasks or a chartered autonomous project. Do not use for implementation, direct review, Hunk interaction, or general orchestration discussion.
---

# Orchestrating Development

Coordinate authorized delivery tasks and chartered autonomous projects without performing their implementation or independent review. Herdr provides runtime control; this skill provides authority profiles, durable workflow state, dependency scheduling, role handoffs, guarded integration, recovery, and human boundaries.

## Activation gate

Fresh controller bootstrap: after verifying Herdr, inspect live agents and claim `workflow_orchestrator` with the current pane ID only when the name is unowned; otherwise reuse the owner or stop for human direction. Do this before reading task records or reporting status.

Before acting, verify all of the following:

1. The user explicitly requested development orchestration rather than advice about orchestration.
2. The current repository's `AGENTS.md` declares it to be an orchestration workspace.
3. `AGENTS.md` and any local configuration file it requires identify allowed repositories or roots, repository-resolution rules, GitHub hosts, and current resource limits.
4. This agent is inside Herdr (`HERDR_ENV=1`) and has loaded Herdr guidance from a discovered skill or `herdr --skill`.
5. Target-repository agents have the skills required by their mode: reviewing-code for reviewers, plus resolving-findings, preparing-pull-requests, and Hunk for development tasks. Every managed product worktree has loaded the packaged managed-role rule before its agent starts, and authors can resolve the configured task-branch publication guard. Delegated and workspace-only tasks require none unless their bounded work independently needs one.
6. The orchestrator is named `workflow_orchestrator`, and the portable managed-agent Herdr rule from [Installation](references/installation.md) is installed for newly launched Codex sessions.
7. Autonomous-project mode has a validated active charter, authoritative source documents, package-record directory, exact non-main integration branch per repository, project-root containment, working-agent ceiling, monitoring cadence, environment/privilege policy, and a passing `./scripts/test-project-squash-merge` result.

If any gate fails, explain the missing prerequisite and stop before creating worktrees, workspaces, agents, or GitHub state. Do not search arbitrary filesystem locations to compensate for missing configuration.

## Required resources

At activation, read the workspace's tracked `AGENTS.md` and every local configuration file it explicitly requires before inspecting or provisioning managed tasks. Then read [Workflow State and Events](references/workflow-state.md) completely. Read [Safety, Capacity, and Escalation](references/safety-and-escalation.md) before provisioning, overlap decisions, permission handling, budget escalation, or cleanup; do not load its cleanup details for an unrelated status-only turn.

When a request concerns an autonomous project, read [Autonomous Project Control](references/project-control.md) completely before reading or creating project state. Use [project-record.yaml](assets/project-record.yaml), [project-work-package-record.yaml](assets/project-work-package-record.yaml), and [project-decision-record.md](assets/project-decision-record.md). The approved product design and implementation plan remain the governing sources; do not substitute the project record for them. Preserve product intent, but adapt the delivery graph under the project-control rules when evidence exposes a better sequence or boundary.

Before starting, replacing, or prompting an author, reviewer, or worker, read [Managed Agent Contracts](references/agent-contracts.md) and prepend the [Managed workflow control block](assets/managed-agent-control-block.md). Only when starting or replacing a role, follow that block with the applicable startup asset:

- [Author startup prompt](assets/author-startup-prompt.md)
- [Reviewer startup prompt](assets/reviewer-startup-prompt.md)
- [External reviewer startup prompt](assets/external-reviewer-startup-prompt.md)
- [Delegated worker startup prompt](assets/delegated-worker-startup-prompt.md)

Before starting, inspecting, or reloading Hunk, read [Hunk Coordination](references/hunk-coordination.md) and use the separately installed Hunk skill for command syntax.

Use [task-record.yaml](assets/task-record.yaml) for development and reviewer-only tasks, [delegated-task-record.yaml](assets/delegated-task-record.yaml) for delegated work, and [workspace-task-record.yaml](assets/workspace-task-record.yaml) for workspace-only work. Do not load eval cases during normal operation.

## Working checklist

Copy this checklist into the orchestration scratchpad and keep one instance per active turn:

- [ ] Verify environment, authority, and current limits.
- [ ] Select `supervised` or `autonomous-project` authority from durable evidence.
- [ ] Complete due hourly/recovery rehydration and bounded transition validation before autonomous-project mutation.
- [ ] Reconcile project, package, and task records with Git, GitHub, Herdr, Hunk, and verification as applicable.
- [ ] Confirm human task authority or chartered package eligibility and requested start state.
- [ ] Enforce the absolute prohibition on product work, pushes, or merges involving `main`; autonomous-project PRs must also never target `main`.
- [ ] Enforce one active package lineage per leased worktree and managed feature workspace.
- [ ] Reserve scope and enforce the chartered working-agent ceiling before starting a role.
- [ ] Start or reuse only the role required for the current transition.
- [ ] Prepend the current managed workflow control block to every role prompt.
- [ ] Validate semantic events before changing workflow state.
- [ ] When autonomous roles are active, honor due watchdog checks without repeatedly prompting healthy workers.
- [ ] Enforce review, scope, permission, role-cardinality, and conflict boundaries.
- [ ] In supervised mode stop at the next human decision; in autonomous-project mode persist the decision or continue to the terminal milestone.

## Orchestration procedure

### 1. Reconcile before creating

For an autonomous project, first apply the context-rehydration procedure in the project-control reference after activation, session resume, detected or suspected compaction, changed governing commits, or context uncertainty. Independently enforce its persisted one-hour lease. Before each named package-start, plan-approval, specification-decision, finalization, merge, or repair/revert gate, validate only the affected records, heads, evidence, and cited authoritative sections against the current checkpoint; repeat full rehydration only when due or when that bounded validation exposes uncertainty. Never treat conversation history or a compaction summary as workflow authority. Persist the completed checkpoint and exact gate identity before mutation.

Inspect active project, package, and task records first. Compare them with authoritative source commits, live Herdr workspaces and named agents, configured worktrees, development targets, reservations, branches, pull requests, checks, evidence, and Hunk sessions. Do not load archived records during normal reconciliation. Recover existing resources rather than creating duplicates. When an older record lacks `development_target`, populate it only from a validated checkout, remote, pull-request base, and branch; use the applicable authority profile when any element is ambiguous.

Before creating another workspace, check whether the request continues an existing task's purpose. If reuse is safe, extend that task and retain its workspace and roles, even when the follow-up adds related submodules, repositories, or pull requests. Names and artifact count do not create a new task boundary; create another workspace only for independent work or necessary isolation.

Treat Herdr `working`, `idle`, `done`, `blocked`, and `unknown` as runtime observations only. Never use them as evidence that planning was approved, implementation finished, review passed, or a permission was granted.

### 2. Discuss what work to pursue

The orchestrator may inspect authorized GitHub issues, direct requests, and repository context to help the human choose work. Present scope, dependencies, likely conflicts, and cost at task-selection depth. Do not develop the implementation plan; that discussion belongs in the author workspace.

Create a supervised task only after explicit human authorization. In autonomous-project mode, create a task only for a dependency-ready package whose scope reservations and capacity were validated under the active charter. Record its authority profile, project/package linkage, cited source sections, integration branch, objective, exclusions, required verification, and reservations without copying the full conversation or author's detailed plan. Give every task a short recognizable `display_name`; retain `task_id` as machine identity and use the live workspace label after provisioning. Record exact repositories, canonical GitHub identities and push URLs, remotes, integration bases, fetched commits, development targets, and issue context. Store active records in the configured task directory, defaulting to `.orchestrator/tasks`.

### 3. Start authorized work with conflict visibility

Read the safety reference and apply the configured overlap and repository policy. Human authority controls supervised parallelism; the charter's dependency graph, reservations, and working-agent ceiling control autonomous parallelism. Resolve rather than guess the exact primary checkout, preserve its state, fetch and record the requested integration-base commit, and create or safely lease one Herdr-managed task workspace from that exact commit. Run only initialization declared by workspace configuration, validate the complete containing-repository context and target, and never start a managed role from a detached, stale, incidental, ambiguous, or `main` branch. Leave product implementation and builds to the managed role.

For a worktree-backed task, invoke Herdr worktree creation directly from the verified canonical primary workspace or checkout and use the workspace returned by that operation. Never create a provisional workspace at the primary checkout first. Treat every non-linked repository workspace as a persistent worktree-group parent; do not close it or try to remove an accidental duplicate. Follow the worktree-group safety procedure instead.

Before starting any managed product role, install the packaged `codex-managed-role.rules` as an ignored workspace-local rule in that task's complete worktree. Use the standard Stagehand agent sandbox and approval settings; do not introduce a stricter launch override merely to enforce publication policy. The explicit command rules and record-aware publisher own that boundary. Verify the rule, process arguments, and configured publisher before sending the first prompt. Rules are loaded at agent startup, so never retrofit this boundary into an already-running role. Then load the Herdr skill and create the required layout without stealing user focus. For development, start one author in the `agents` tab; do not create the reviewer or Hunk yet. For reviewer-only or delegated work, start its sole reviewer or worker. A workspace-only task may contain no managed role until the human requests one. Prepend the rendered control block and applicable template, then verify the task, role, and orchestrator acknowledgement before directing the human to it. The complete review topology is defined in [Hunk Coordination](references/hunk-coordination.md). Never start a fixer, helper, or speculative agent.

### 4. Leave implementation planning with the author

For development tasks, set the task to `planning`. A supervised author proposes its plan to the human in its pane. An autonomous-project author cites the authoritative documents and sends `plan-proposed`; the orchestrator is the approval actor and validates scope, contracts, exclusions, abstractions, reusable verification, reservations, and package completion coverage. Return bounded corrections until the plan agrees, then authorize it with a fresh implementation control block without a routine human checkpoint. Ask the human only when the plan requires authority outside the charter. The author must successfully deliver `implementation-started` before editing. A fallback preserves approval evidence but stops the author until recovery.

Retain the recoverable plan reference, approved scope identity, source sections, verification obligations, and conflict-relevant ownership without copying the full plan. If the author or reviewer reports a specification gap, follow the ADR and package-invalidation procedure in the project-control reference; never approve an implementation-only divergence.

### 5. Monitor through events and Herdr

Managed agents prompt `workflow_orchestrator` with semantic events. Validate every event against the task record, expected role, repository, branch, PR, scope version, and current head before transitioning.

Every orchestrator-to-role instruction must begin with a newly rendered control block populated from the same task-record transition expectation used for event validation. Persist the expected role and allowed success or blocker events; never rely on conversational memory or permit a role to invent event names.

Apply the shared-input collision and bounded furthest-proven-state reconciliation procedures in [Workflow State and Events](references/workflow-state.md) on every monitoring or reporting turn. Use Herdr lifecycle only to target investigation and validate every skipped authority and artifact boundary. Return supervised ambiguity to the human; in autonomous-project mode use the chartered decision and recovery procedure unless authority truly lies outside the charter.

In supervised mode, reconcile on the next monitoring or task request. In autonomous-project mode, the kickoff authorizes the low-frequency attached watchdog in the project-control reference: events remain the fast path, but due batched lifecycle sweeps recover missed signals and enforce the next full-rehydration due time. Use bounded waits where they avoid model turns, inspect transcripts only for settled, overdue, blocked, unknown, or contradictory roles, and back off for healthy long operations. Never busy-poll or repeatedly prompt workers for progress.

When an agent is blocked on permission, follow the permission-escalation procedure. Never send approval input on the human's behalf. Managed roles never attempt privilege escalation or host network/system mutation; portable simulations run normally, while privileged scenarios remain unexecuted human-gated evidence.

### 6. Direct initial draft creation

On a validated `implementation-ready`, atomically set draft creation and publication authority for the exact author, task branch, remote, and verified head, then send the original author a `drafting` control block allowing only applicable draft or blocker events. Direct it to use the preparing-pull-requests skill for content, then publish and create the draft through the configured task-branch guard rather than `git push` or `gh pr create`; the guarded draft operation must use that explicit already-pushed remote head. Require the exact recorded base; autonomous PRs target the integration branch and never `main`. Require the description to cite confirmed intent, authoritative source sections, boundaries, decisions, reusable-test changes, exact verification, and limitations. Clear both authorities after accepting the matching `draft-pr-ready` event; issue a new exact-head publication authorization for each later fixes publication.

Accept `draft-pr-ready` only for a recoverable draft pull request whose current remote head matches the event and whose description contains the intended review context.

### Reviewer-only path

For an explicitly authorized reviewer-only task, resolve the existing pull request and exact current base and head before creating the worktree. Start one reviewer with the external reviewer prompt; do not create an author or Hunk session. The reviewer must leave source and pull-request state unchanged while producing a recoverable proposed GitHub review.

On `review-proposed`, validate the proposal artifact, conclusion, pull request, and unchanged head, then present the exact proposed review to the human. Do not infer publication approval from task authorization or a favorable conclusion.

Only after explicit human authorization for that exact proposal and head may the same reviewer publish it. Require `review-published`, verify the published review matches the authorization, and enter `review-complete`. If the head changes before publication, invalidate the proposal and require a complete rereview. Ask whether to retain the workspace for a later rereview or clean it up; do not modify the PR branch, description, labels, draft state, readiness, or merge state.

### Delegated-work path

Use delegated work for bounded investigation, diagnosis, planning, or research with no intended landed repository change. Start one worker at the recorded target with the authorized objective and mutation boundary; tracked source is read-only by default. It has no author, reviewer, Hunk, PR, or review loop.

Accept only `work-complete` or `needs-human`. Validate any `resultRef`, present the result, and enter `delegated-complete`; cleanup remains human-directed. If the desired outcome becomes a landed change, stop and obtain authorization for a development task rather than silently expanding this mode.

### Workspace-only path

Use workspace-only mode when the human requests an isolated checkout for open-ended, human-directed work without committing to a managed delivery workflow. At the human's request it may host one `workspace_agent`, but that agent remains human-directed and sends no managed workflow events until promotion. Record the task's purpose and ownership without inventing author, reviewer, Hunk, PR, or event stages.

When work from that workspace becomes a pull request or managed implementation, prefer promoting the same task to development over creating a parallel task. Preserve its task, workspace, worktree, and existing agent; treat assigning that agent as author as a role start, safely reconcile the checkout and record to the durable branch and pull-request head, then resume at the furthest proven development state. If unrelated or unrecoverable local work prevents safe reuse, preserve it and ask the human rather than switching or duplicating silently.

### 7. Begin independent review

Check supervised review budgets or autonomous convergence state before proceeding.

Apply the fixed topology from [Hunk Coordination](references/hunk-coordination.md): split the author pane toward the right inside the existing `agents` tab and start or reuse the independent reviewer there; create the separate full-width `hunk` tab with `--cwd` set to the exact recorded development target, verify that cwd before launch, and start one non-watching session through the validated wrapper. Verify its repository, base, and head. Prompt the reviewer with a `reviewing` control block containing the exact allowed outcomes, followed by its role instructions. The reviewer must use the reviewing-code and Hunk skills and review the complete current changeset.

The reviewer must obtain intent from the PR description, comments, linked issue or requirements, authoritative design and implementation-plan sections, ADRs, package completion criteria, and current head before analyzing code. Do not substitute the orchestrator's abbreviated records for those sources.

### 8. Route findings without expanding scope

On `review-findings`, validate the reviewed head and preserve the outcome before Hunk reload. Under supervised `human-selection`, present material findings for human disposition. Under an autonomous charter, the orchestrator selects all material in-scope findings, rejects follow-up expansion, and routes specification questions through the ADR procedure. A standing policy never absorbs unrelated improvements or undocumented scope expansion.

Prompt the original author with only the selected set. Keep Hunk unchanged until the author has consumed the comments, resolved the selected findings, updated the draft head, and emitted `fixes-ready`. Then reload Hunk explicitly against the recorded base and new head and ask the same reviewer for a complete rereview.

### 9. Control loops and scope versions

Increment review counters only for accepted complete-review outcomes. Supervised mode stops at its configured numeric limits unless the human continues. Autonomous-project mode has no numeric human stop; enforce repeated-finding, no-progress, incompatible-conclusion, stale-head, and resource controls from the project reference.

Keep `scope-revised` available for supervised tasks. Human-authorized supervised changes and charter-authorized documented project decisions create new scope versions. Verify their authority, update owning documents and ADRs where material, invalidate affected package assumptions, increment the scope version, preserve cumulative usage, reset only the per-scope review count, update durable intent, and require a new full phase-zero review.

Escalate repeated findings, no-progress fixes, contradictory events, author-reviewer deadlock, unexpected head changes, overlapping work, or long-running notices according to the safety reference. Do not respond by spawning another agent or silently widening the task.

### 10. Route finalization through the human

A valid `review-passed` for the unchanged current head creates a `ready-candidate`. Reconcile the reviewed head, remaining risk, specification alignment, decisions, verification, limitations, and review usage.

In supervised mode, ask for explicit human finalization authorization. In autonomous-project mode, the active charter permits the orchestrator to authorize reviewer finalization after every package evidence gate passes. Require `pull-request-finalized` for the exact head.

Validate the finalized head, ready state, integration base, issue linkage, description, source citations, decisions, verification, and package completion criteria. In supervised mode, mark it `ready-for-team-review` and return merge authority to the human. In autonomous-project mode, set the delivery and package to `merge-ready`, then invoke `./scripts/project-squash-merge` with the exact project record, package record, repository key, PR, base, and head. Persist the returned merge commit, verify one squash commit reached the integration branch, run required post-merge evidence, and only then unlock successors.

Never merge except through the guarded autonomous-project squash procedure. Never enable auto-merge, use administrator bypass, use merge/rebase strategies, push an integration branch directly after creation, begin unauthorized work, or mutate or merge `main`.

### 11. Reenter review after human feedback

Supervised human-selected feedback or autonomous orchestrator-selected material findings after `review-passed` or `pull-request-finalized` return the task to the original author-reviewer loop. Follow the workflow-state and role contracts: bind only the selected feedback, invalidate prior reviewed and finalized heads, classify the change as `small-fix` or `material`, and apply the configured draft-state policy without transferring independent review ownership.

Route the selected set through the finding-resolution contract. Any new head requires complete rereview by the same reviewer and new authorization from the recorded approval actor; GitHub replies and thread resolution remain separate actions.

### 12. Clean up task resources

After a verified merge or explicit human cleanup request, follow the guarded cleanup procedure. Autonomous project workspaces may instead return to the configured pool only after the project-control lease audit. Remove or re-lease only recorded resources after proving recoverability; preserve ambiguity. Treat PR closure, branch deletion, and other worktrees separately.

## Status reporting

For an autonomous project check-in or final report, first show the project title, charter state, source-document commit, integration head per repository, working-agent usage, completed/total package count, current critical path, verification summary, and important ADRs since the previous report. Include blocked and eligible packages even when they have no task workspace yet. Do not expose private local configuration.

End every user-visible response with one row for each non-`cleaned` task or nonterminal project package; a newly cleaned task or integrated package may appear once. Use exactly four columns:

| Workspace / work item | Stage | Agents | PR |
| --- | --- | --- | --- |
| 🟡 `settings-button-rows` · [example-app#772 Settings button rows](<issue-url>) | `<state>` | `Author idle · fixed r1; Reviewer idle · passed r2 → you` | `[#<pr>](<pr-url>) or —` |

Above the table, show `🔴 needs you · 🟡 in progress · 🟢 orchestration complete`. Derive color after reconciliation: settled task states (`ready-for-team-review`, `review-complete`, `delegated-complete`, `merged`, `closed`) and integrated packages are green; other items with `attention_required` are red; all others are yellow. Do not persist color or inherit it from dependencies.

Formatting rules:

- Lead provisioned tasks with the exact live Herdr sidebar label in code, followed when useful by a short repository-qualified issue link and title. Reuse that label throughout the response. Before provisioning, use `<display name> (workspace not created)`. Derive and persist a missing legacy `display_name` once; do not query GitHub only to render it. Disambiguate duplicate live labels with the workspace ID.
- Show workflow state in `Stage`; add scope after version 1 and review usage only when relevant.
- In `Agents`, pair each role's current Herdr lifecycle with only the latest accepted milestone needed to disambiguate the cycle: `implementing`, `reviewing r2`, `findings r2`, `fixing r2`, `fixed r2`, `passed r3`, or `work complete`. Rounds are per scope; `fixing r2` answers findings from round 2. When settled roles obscure ownership, append `→ Author`, `→ Reviewer`, or `→ you`. Use `—` for roles not yet created.
- Link the PR when known. Keep CI, dependencies, internal wait state, and notes out of the table unless they require human disposition.
- Preserve task order. Use one bounded Herdr inventory for live labels and lifecycle, and durable records for workflow state. Persist renamed workspace labels; flag missing live workspaces instead of substituting issue numbers.

Finish with a section titled exactly `Needs your attention`. List concrete decisions outside the active authority profile first, then supervised handoffs awaiting final human review or merge. Chartered project decisions, ordinary dependency waits, and informational status do not belong here. Each item starts with the same workspace or package label and contains one action. Write `None.` when no human action is required. Nothing follows this section.
