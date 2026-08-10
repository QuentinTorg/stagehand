# Safety, Capacity, and Escalation

## Configuration contract

The orchestration repository's tracked `AGENTS.md` must declare that orchestration is enabled. It may require an ignored local configuration file for allowed repository roots or named repositories, repository-resolution rules, GitHub hosts, and local limit overrides. Model preferences, workspace-label conventions, repository-specific initialization, and a task-record directory may also live in that local file. Read the complete configuration chain before acting; a referenced local file is part of the activation contract, not an optional hint.

When no task-record directory is configured, use `.orchestrator/tasks` inside the orchestration repository. Keep runtime task records out of product repositories and ignore them from version control when they contain machine-specific paths or private task context.

Missing configuration is not permission to search the filesystem or guess among similarly named checkouts. Ask the human for the exact repository path and record it only in the local configuration when requested. Never copy the complete local configuration into a managed-agent prompt or a public artifact.

## Workload authority and loop limits

The human decides how many explicitly authorized workflows run concurrently. The orchestrator does not impose a default global task, worktree, or working-agent limit. It reports the current workload when relevant and never creates speculative work merely because resources are available.

The following per-task limits still apply unless the workspace configuration is stricter or the human explicitly changes them:

- each task owns one workspace and one worktree; a development task has one author and one reviewer, while a reviewer-only task has one reviewer and no author;
- managed agents do not spawn additional agents;
- each scope version receives at most three accepted review outcomes;
- each task receives at most six accepted review outcomes total; and
- a third material scope revision requires a progress and cost check.

## Parallel-work overlap checks

Every task requires explicit human authorization. Before starting it, compare it with executing tasks using repository identity, base, task brief, known affected paths, current diffs, submodule revisions, dependent pull requests, and shared build state.

When tasks may modify the same contract, files, generated artifacts, submodule pointer, database schema, deployment surface, or shared build output, explain the likely conflict and recommend sequencing. Ask the human whether to wait or proceed; do not silently block an explicitly confirmed parallel task. Never solve overlap by putting two tasks into one workspace.

## Permission handling

The installed managed-agent workflow rule may automatically allow caller-pane discovery, semantic event delivery to `workflow_orchestrator`, and the bounded Hunk session operations documented by the installation guide. The orchestration workspace may additionally authorize its validated Hunk launcher and interrupt-only wrapper. These permissions do not authorize arbitrary pane input, approval keys, comment deletion, or destructive commands.

Use `./scripts/herdr-interrupt-agent <agent-name>` only for a task-owned agent whose current work has been invalidated by a newer human instruction, or when interruption is needed to prevent an external mutation that is no longer authorized. Inspect the named agent and its recent output first. The wrapper sends only Escape; it does not authorize Enter, Ctrl+C, approval responses, or arbitrary keys.

Version one never interacts with an agent's permission UI. When Herdr reports `blocked` or a request is visible for another operation:

1. identify the exact task, role, command or action, target, and stated reason;
2. determine whether the request is still current;
3. present a concise recommendation and risk to the human; and
4. wait for the human to act or explicitly direct the orchestrator.

Do not send Enter, approval keys, credentials, or broad authorization to unblock an agent. Routine workflow language is not an allowlist; automatic approval requires a separately installed, evaluated rule with a narrow command boundary.

## No-progress and cost controls

Escalate instead of looping when any of these occurs:

- the per-scope or total review budget is reached;
- substantially the same finding returns after an attempted resolution;
- a fix round produces no material relevant diff;
- author and reviewer reach incompatible conclusions twice;
- an expected event is missing, malformed, stale, or repeatedly contradictory;
- the active branch or PR head changes from an unknown source;
- an agent remains working beyond the configured notice interval; or
- repository overlap appears after work begins.

A long-running build is not automatically failure. Report its elapsed time and observed output without canceling it unless the human or repository policy supplies a timeout. Because Herdr does not report token usage, use task counts, turns, rounds, elapsed-time notices, and explicit status summaries to give the human useful cost visibility.

## Human checkpoints

Always require the human for:

- initial task authorization and the decision to proceed with likely conflicting parallel work;
- implementation-plan approval in the author session;
- material intent or scope changes;
- disposition not covered by an explicit selected-finding policy;
- risky, destructive, external, credentialed, or out-of-root operations;
- continuation beyond review or scope-revision budgets;
- reviewer finalization of a ready candidate; and
- publication of a reviewer-only task's proposed GitHub review; and
- conflict resolution between parallel tasks.

Initial development-task authorization covers routine feature-branch publication and initial draft creation by the author. It does not cover reviewer finalization, publication of reviewer-only output, policy exceptions, or merge. The human authorizes reviewer finalization or external review publication and performs every merge after reviewing the finalized pull request.

Selected post-readiness feedback authorizes only its bounded resolution. Returning a materially changing pull request to draft requires explicit human authority or a standing workspace policy; ambiguity returns to the human. Neither feedback selection nor draft return authorizes GitHub thread replies, thread resolution, unrelated PR edits, or reuse of the previous review conclusion.

## Cleanup authority

A verified merged pull request implicitly authorizes cleanup of that task's Herdr workspace and worktree. The human may also explicitly request cleanup before merge. Neither condition alone authorizes force removal, pull-request closure, branch deletion, or loss of local work; only the narrowly audited force paths below extend ordinary cleanup authority.

Before cleanup, verify task ownership, PR state when applicable, and agent/process state, then audit a meta-repository worktree at two distinct layers:

1. **Inside every initialized submodule:** require no internal tracked modifications or untracked files. For the development target, prove every task commit is recoverable from the recorded remote branch, pull-request head, merged pull request, or another explicit durable reference. For non-target submodules, also require their expected pinned identity. Internal product changes, commits whose recoverability is uncertain, or an active process whose work must survive always block cleanup.
2. **In the containing repository:** require no tracked or untracked changes except an expected gitlink difference for the recorded development target. That one difference is disposable without another human decision only when the task record says `containing_repository_pointer_update: not-planned` and the target passed the internal recoverability audit. A planned or ambiguous pointer update remains work that must be preserved.

For a legacy task without the pointer-update field, reconcile it once from an explicit recorded scope statement or standing workspace policy. Persist `not-planned` only when that authority clearly excludes a containing-repository update; otherwise ask the human and persist the answer. Do not repeatedly ask after the disposition is durable.

Do not describe an allowed target gitlink difference as a dirty or out-of-date submodule, reset the target to the containing repository's pin, or require a containing-repository pull request that the task explicitly excludes.

After both audit layers pass:

1. deinitialize clean pinned submodules normally;
2. when the recorded target alone differs from its containing gitlink and its pointer update is `not-planned`, run `git submodule deinit -f -- <validated-relative-target-path>` from the task-owned containing worktree if ordinary deinitialization would refuse that expected mismatch; and
3. ask Herdr to remove the task workspace and worktree normally.

The `-f` exception applies only to the exact recorded target after its internal cleanliness and remote recoverability were proven. Never combine it with `--all`, use it on an unrecorded or ambiguous path, use it in the primary checkout, or use it to dispose of internal modifications, untracked files, unpushed commits, or running work. If scoped deinitialization fails, or normal Herdr removal fails for any reason other than the specific linked-worktree submodule prohibition handled below, preserve the worktree and diagnose rather than broadening force.

When every submodule is deinitialized and normal Herdr removal fails solely with Git's prohibition on removing a linked worktree from a repository containing submodules, revalidate immediately that the workspace ID and checkout belong to the task, every managed agent is settled, no blocked interaction or independent build/test/server/editor process has state that must survive, no submodule remains initialized, and no unrecoverable file or commit remains. Do not require an empty process list: idle or done Codex agents, completed Hunk sessions, and ordinary shells are task-owned workspace runtimes that Herdr force is designed to shut down. Standing cleanup authority then permits:

```text
herdr worktree remove --workspace <recorded-workspace-id> --force --json
```

Herdr's force path shuts down the selected workspace's terminal runtimes and invokes `git worktree remove --force` for that recorded checkout. Settled agents and disposable Hunk or shell processes are not an `active workspace` for this purpose; a working agent, blocked human interaction, or independent process with state that must survive is active. The force path does not authorize another workspace, the primary checkout, a dirty or active workspace, branch deletion, manual recursive deletion, or a second broader force operation. If the audited command fails, preserve the remaining state and diagnose the exact failure.

A successor or follow-up task does not keep its predecessor workspace alive merely because the new work remains active. When the tasks have distinct recorded worktrees and every predecessor change that must survive is recoverable in the successor's remote branch, pull request, or another durable reference, audit and clean the predecessor independently. Preserve it only when unique predecessor-local work, a shared process, or ambiguous ownership remains.

Preserve the workspace and ask the human when internal product work, unexpected containing-repository changes, unpushed commits, an active process has state that must survive, ownership is shared, or ambiguity remains. Settled task-owned terminal runtimes are disposed through the audited Herdr path above. Close and remove only resources recorded for that task.

## Prohibited behavior

The orchestrator must not edit product code, become the author or reviewer, create speculative tasks, start work merely because capacity exists, recursively spawn agents, push to `main`, force-push, merge, enable auto-merge, bypass checks, change policy, clean unknown worktrees, or terminate processes it does not own.
