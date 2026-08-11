---
name: orchestrating-development
description: Use only when the user explicitly asks the designated agent in a repository configured as an orchestration workspace to start, coordinate, monitor, resume, or report on development or reviewer-only tasks through Herdr-managed sessions. Do not use for ordinary implementation, direct review, Hunk interaction, or orchestration discussion.
---

# Orchestrating Development

Coordinate authorized development and reviewer-only tasks without becoming their planner, author, reviewer, fixer, or merger. Herdr provides runtime control; this skill provides workflow state, role handoffs, conflict visibility, loop limits, and human authority boundaries.

## Activation gate

Before acting, verify all of the following:

1. The user explicitly requested development orchestration rather than advice about orchestration.
2. The current repository's `AGENTS.md` declares it to be an orchestration workspace.
3. `AGENTS.md` and any local configuration file it requires identify allowed repositories or roots, repository-resolution rules, GitHub hosts, and current resource limits.
4. This agent is inside Herdr (`HERDR_ENV=1`) and the repository-local Herdr skill is available.
5. Target-repository agents will have the skills needed for their assigned mode: reviewing-code for every reviewer, plus resolving-findings, preparing-pull-requests, and Hunk for development tasks.
6. The orchestrator is named `workflow_orchestrator`, and the portable managed-agent Herdr rule from [Installation](references/installation.md) is installed for newly launched Codex sessions.

If any gate fails, explain the missing prerequisite and stop before creating worktrees, workspaces, agents, or GitHub state. Do not search arbitrary filesystem locations to compensate for missing configuration.

## Required resources

At activation, read the workspace's tracked `AGENTS.md` and every local configuration file it explicitly requires before inspecting or provisioning managed tasks. Then read [Workflow State and Events](references/workflow-state.md) completely. Read [Safety, Capacity, and Escalation](references/safety-and-escalation.md) before provisioning, overlap decisions, permission handling, budget escalation, or cleanup; do not load its cleanup details for an unrelated status-only turn.

Before starting, replacing, or prompting an author or reviewer, read [Managed Agent Contracts](references/agent-contracts.md) and prepend the [Managed workflow control block](assets/managed-agent-control-block.md). Only when starting or replacing a role, follow that block with the applicable startup asset:

- [Author startup prompt](assets/author-startup-prompt.md)
- [Reviewer startup prompt](assets/reviewer-startup-prompt.md)
- [External reviewer startup prompt](assets/external-reviewer-startup-prompt.md)

Before starting, inspecting, or reloading Hunk, read [Hunk Coordination](references/hunk-coordination.md) and use the separately installed Hunk skill for command syntax.

Use [task-record.yaml](assets/task-record.yaml) when creating a task record. Do not load eval cases during normal operation.

## Working checklist

Copy this checklist into the orchestration scratchpad and keep one instance per active turn:

- [ ] Verify environment, authority, and current limits.
- [ ] Reconcile existing task records with Git, GitHub, Herdr, and Hunk as applicable.
- [ ] Confirm the human-authorized task and requested start state.
- [ ] Enforce one task per worktree and managed feature workspace.
- [ ] Start or reuse only the role required for the current transition.
- [ ] Prepend the current managed workflow control block to every role prompt.
- [ ] Validate semantic events before changing workflow state.
- [ ] Enforce review, scope, permission, role-cardinality, and conflict boundaries.
- [ ] Stop at the next human decision or report the validated outcome.

## Orchestration procedure

### 1. Reconcile before creating

Inspect task records first. Compare them with live Herdr workspaces and named agents, configured worktrees, development targets, branches, draft pull requests, and Hunk sessions. Recover existing resources rather than creating duplicates. When an older record lacks `development_target`, populate it only from a validated checkout, remote, pull-request base, and branch; ask the human when any element is ambiguous.

Treat Herdr `working`, `idle`, `done`, `blocked`, and `unknown` as runtime observations only. Never use them as evidence that planning was approved, implementation finished, review passed, or a permission was granted.

### 2. Discuss what work to pursue

The orchestrator may inspect authorized GitHub issues, direct requests, and repository context to help the human choose work. Present scope, dependencies, likely conflicts, and cost at task-selection depth. Do not develop the implementation plan; that discussion belongs in the author workspace.

Create a task only after explicit human authorization. Record whether it is a development or reviewer-only task and capture the objective and boundaries compactly without copying the full conversation. Give every task a short, recognizable `display_name`, normally based on the GitHub issue or pull-request title when one exists; use it as the human-facing fallback until a Herdr workspace exists, while `task_id` remains the stable machine identity and the live workspace label becomes the primary human identity after provisioning. Record the containing checkout's verified remote, requested base, and fetched base commit. Record the exact development target separately: root repository or submodule path, verified remote, intended pull-request base, fetched base commit, and feature branch. For a submodule target, also record whether a containing-repository pointer update is `not-planned` or `planned`; do not infer this during cleanup from a modified gitlink. When the development source is GitHub, record and pass the issue repository, number, and URL so the author can link the draft correctly. Initial development-task authorization includes routine feature-branch publication and initial draft creation. Store the task record in the configured task-record directory, defaulting to `.orchestrator/tasks` inside this repository.

### 3. Start authorized work with conflict visibility

Read the safety reference and apply the configured overlap and repository policy. The human controls authorized parallelism; recommend sequencing for likely conflicts without imposing a fixed cap. Resolve rather than guess the exact primary checkout, preserve its state, fetch and record the requested remote-base commit, and create one Herdr-managed feature workspace from that exact commit. Run only initialization declared by the workspace configuration, validate the resulting root or submodule development target, and never start an author from a detached, stale, incidental, or ambiguous branch. Use the validated checkout as the command working directory and leave product instructions and builds to the managed role.

Load the Herdr skill and create the required layout without stealing user focus. For a development task, create the `agents` tab and start one named author there using the rendered control block followed by the filled author template; do not create the reviewer or `hunk` tab yet. Verify its first response contains the expected task, role, and orchestrator acknowledgement before directing the human to it. For a reviewer-only task, apply the same launch contract to its reviewer. The complete review topology is defined in [Hunk Coordination](references/hunk-coordination.md). Never start a fixer, helper, or speculative agent.

### 4. Leave implementation planning with the author

Set the task to `planning` and direct the human to the author pane. The author may explore read-only and propose its plan. It must receive approval in that session and successfully deliver `implementation-started` before editing. A fallback preserves the approval evidence but stops the author until the orchestrator recovers the event.

The orchestrator does not need the detailed plan. Retain only the task brief, approved scope identity, constraints needed for coordination, and any conflict-relevant affected areas.

### 5. Monitor through events and Herdr

Managed agents prompt `workflow_orchestrator` with semantic events. Validate every event against the task record, expected role, repository, branch, PR, scope version, and current head before transitioning.

Every orchestrator-to-role instruction must begin with a newly rendered control block populated from the same task-record transition expectation used for event validation. Persist the expected role and allowed success or blocker events; never rely on conversational memory or permit a role to invent event names.

Apply the shared-input collision and bounded furthest-proven-state reconciliation procedures in [Workflow State and Events](references/workflow-state.md) on every monitoring or reporting turn. Use Herdr lifecycle only to target investigation, validate every skipped authority and artifact boundary, and return ambiguity to the human rather than waiting indefinitely or replaying obsolete handoffs.

Between active orchestrator turns, rely on explicit agent events plus Herdr's visible status and notifications; do not create an unbounded polling or cron loop inside the agent. A failed event delivery cannot wake an idle orchestrator, so this version detects silent failures on the orchestrator's next invocation. Use bounded waits only when the user explicitly asks the orchestrator to remain attached and monitor.

When an agent is blocked on permission, follow the permission-escalation procedure. Never send approval input on the human's behalf.

### 6. Direct initial draft creation

On a validated `implementation-ready`, send the original author a `drafting` control block allowing only `draft-pr-ready` or `needs-human`, followed by the instruction to use the preparing-pull-requests skill to publish the feature branch and create the initial draft. This does not require another human authorization. Require the draft to preserve confirmed intent and link the originating GitHub issue when present.

Accept `draft-pr-ready` only for a recoverable draft pull request whose current remote head matches the event and whose description contains the intended review context.

### Reviewer-only path

For an explicitly authorized reviewer-only task, resolve the existing pull request and exact current base and head before creating the worktree. Start one reviewer with the external reviewer prompt; do not create an author or Hunk session. The reviewer must leave source and pull-request state unchanged while producing a recoverable proposed GitHub review.

On `review-proposed`, validate the proposal artifact, conclusion, pull request, and unchanged head, then present the exact proposed review to the human. Do not infer publication approval from task authorization or a favorable conclusion.

Only after explicit human authorization for that exact proposal and head may the same reviewer publish it. Require `review-published`, verify the published review matches the authorization, and enter `review-complete`. If the head changes before publication, invalidate the proposal and require a complete rereview. Ask whether to retain the workspace for a later rereview or clean it up; do not modify the PR branch, description, labels, draft state, readiness, or merge state.

### 7. Begin independent review

Check review budgets before proceeding.

Apply the fixed topology from [Hunk Coordination](references/hunk-coordination.md): split the author pane toward the right inside the existing `agents` tab and start or reuse the independent reviewer there; create the separate full-width `hunk` tab with `--cwd` set to the exact recorded development target, verify that cwd before launch, and start one non-watching session through the validated wrapper. Verify its repository, base, and head. Prompt the reviewer with a `reviewing` control block containing the exact allowed outcomes, followed by its role instructions. The reviewer must use the reviewing-code and Hunk skills and review the complete current changeset.

The reviewer must obtain intent from the GitHub pull-request description, comments, linked issue or requirements, and current head before analyzing the code. Do not substitute the orchestrator's abbreviated task record for that GitHub context.

### 8. Route findings without expanding scope

On `review-findings`, validate the reviewed head and preserve the outcome before Hunk reload. Under the default `human-selection` policy, present the material findings for human disposition. Apply a standing policy only when the task record contains an explicit human-authorized rule; it may never absorb follow-up candidates, judgment-required changes, or scope expansion.

Prompt the original author with only the selected set. Keep Hunk unchanged until the author has consumed the comments, resolved the selected findings, updated the draft head, and emitted `fixes-ready`. Then reload Hunk explicitly against the recorded base and new head and ask the same reviewer for a complete rereview.

### 9. Control loops and scope versions

Increment review counters only for accepted complete-review outcomes. Stop at three rounds in one scope version or six total unless the human explicitly continues.

Only a human-authorized material change creates a new scope version, signaled by `scope-revised` during ordinary development or a material `post-review-changes-started` after successful review. Increment the scope version, preserve cumulative usage, reset only the per-scope review count, update durable intent, and require a new full phase-zero review. After the configured scope-revision threshold, provide a progress and cost summary before continuing.

Escalate repeated findings, no-progress fixes, contradictory events, author-reviewer deadlock, unexpected head changes, overlapping work, or long-running notices according to the safety reference. Do not respond by spawning another agent or silently widening the task.

### 10. Route finalization through the human

A valid `review-passed` for the unchanged current head creates a `ready-candidate`. Summarize the reviewed head, remaining risk, verification, limitations, and review-round usage, then ask whether the reviewer may finalize.

Only after explicit human authorization may the reviewer use the preparing-pull-requests skill to reconcile reviewer-owned context and mark that exact head ready for team review. Require the reviewer to emit `pull-request-finalized` afterward.

Validate the finalized head, ready state, issue linkage, description, verification summary, and material deviations from the original task brief. If they agree, mark the task `ready-for-team-review` and ask the human to perform the final GitHub review and merge decision. If the delivered result materially deviates, flag it clearly and return to human disposition rather than requesting merge.

Never merge, enable auto-merge, begin another unauthorized task, or treat readiness as GitHub approval.

### 11. Reenter review after human feedback

Human-selected feedback after `review-passed` or `pull-request-finalized` returns the task to the original author-reviewer loop. Follow the post-review transition in [Workflow State and Events](references/workflow-state.md) and the role boundaries in [Managed Agent Contracts](references/agent-contracts.md): bind only the selected feedback, invalidate prior reviewed and finalized heads, classify the change as `small-fix` or `material`, and apply the configured draft-state policy without transferring readiness ownership to the orchestrator or author.

Route the selected set through the finding-resolution contract. Any new head requires a complete rereview by the same reviewer and new human-authorized finalization; GitHub replies and thread resolution remain separate explicit actions.

### 12. Clean up task resources

After a verified merge or explicit human cleanup request, follow the complete guarded cleanup procedure in the workflow-state and safety references. Remove only the recorded task workspace and worktree after proving recoverability; preserve ambiguous state. Treat pull-request closure, branch deletion, and other task worktrees as separate concerns.

## Status reporting

End every user-visible response with one row for each non-`cleaned` task; a newly cleaned task may appear once. Use exactly four columns:

| Workspace / work item | Stage | Agents | PR |
| --- | --- | --- | --- |
| 🟡 `settings-button-rows` · [example-app#772 Settings button rows](<issue-url>) | `<state>` | `Author idle · fixed r1; Reviewer idle · passed r2 → you` | `[#<pr>](<pr-url>) or —` |

Above the table, show `🔴 needs you · 🟡 in progress · 🟢 orchestration complete`. Derive color after reconciliation: settled states (`ready-for-team-review`, `review-complete`, `merged`, `closed`) are green; other tasks with `attention_required` are red; all others are yellow. Do not persist color or inherit it from dependencies.

Formatting rules:

- Lead provisioned tasks with the exact live Herdr sidebar label in code, followed when useful by a short repository-qualified issue link and title. Reuse that label throughout the response. Before provisioning, use `<display name> (workspace not created)`. Use internal IDs only to resolve ambiguity.
- Show workflow state in `Stage`; add scope after version 1 and review usage only when relevant.
- In `Agents`, pair each role's current Herdr lifecycle with only the latest accepted milestone needed to disambiguate the cycle: `implementing`, `reviewing r2`, `findings r2`, `fixing r2`, `fixed r2`, or `passed r3`. When settled roles obscure ownership, append `→ Author`, `→ Reviewer`, or `→ you`. Use `—` for roles not yet created.
- Link the PR when known. Keep CI, dependencies, internal wait state, and notes out of the table unless they require human disposition.
- Preserve task order. Use one bounded Herdr inventory for live labels and lifecycle, and durable records for workflow state. Persist renamed workspace labels; flag missing live workspaces instead of substituting issue numbers.

Finish with a section titled exactly `Needs your attention`. List concrete blocking decisions first, then completed handoffs awaiting final human review or merge. Each item starts with the same workspace label and contains one action. Omit passive waits and informational status; write `None.` when no action is required. Nothing follows this section.
