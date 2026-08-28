# Safety, Capacity, and Escalation

## Configuration contract

The orchestration repository's tracked `AGENTS.md` must declare that orchestration is enabled. It may require an ignored local configuration file for allowed repository roots or named repositories, repository-resolution rules, GitHub hosts, and local limit overrides. Model preferences, workspace-label conventions, repository-specific initialization, and a task-record directory may also live in that local file. Read the complete configuration chain before acting; a referenced local file is part of the activation contract, not an optional hint.

When no task-record directory is configured, use `.orchestrator/tasks` inside the orchestration repository. Keep runtime task records out of product repositories and ignore them from version control when they contain machine-specific paths or private task context.

Missing configuration is not permission to search the filesystem or guess among similarly named checkouts. Ask the human for the exact repository path and record it only in the local configuration when requested. Never copy the complete local configuration into a managed-agent prompt or a public artifact.

## Workload authority and loop limits

The human decides how many explicitly authorized workflows run concurrently. The orchestrator does not impose a default global task, worktree, or working-agent limit. It reports the current workload when relevant and never creates speculative work merely because resources are available.

The following per-task limits still apply unless the workspace configuration is stricter or the human explicitly changes them:

- each task owns one workspace and one worktree; development has one author and reviewer, reviewer-only one reviewer, and delegated work one worker;
- managed agents do not spawn additional agents;
- each scope version receives at most three accepted review outcomes;
- each task receives at most six accepted review outcomes total; and
- a third material scope revision requires a progress and cost check.

## Parallel-work overlap checks

Every task requires explicit human authorization. Before starting it, compare it with executing tasks using repository identity, base, task brief, known affected paths, current diffs, submodule revisions, dependent pull requests, and shared build state.

When tasks may modify the same contract, files, generated artifacts, submodule pointer, database schema, deployment surface, or shared build output, explain the likely conflict and recommend sequencing. Ask the human whether to wait or proceed; do not silently block an explicitly confirmed parallel task. Never solve overlap by putting two tasks into one workspace.

## Herdr worktree-group safety

Herdr groups a primary checkout's non-linked workspace with every linked worktree workspace sharing its repository identity. Closing that parent can terminate the entire group, including unrelated agents, while the CLI reports only success.

For a worktree-backed task:

1. Reconcile the existing canonical primary workspace and linked task workspaces.
2. Run `herdr worktree create` once, using that primary workspace or confirmed checkout as the source.
3. Parse and record the task workspace returned by Herdr.

Do not create a provisional workspace at the primary checkout, create a second non-linked parent, or use `herdr workspace close` during provisioning or cleanup. Never use pane or tab closure to bypass that prohibition when it would close a non-linked workspace. If a duplicate parent or mistaken workspace is created, preserve it, stop further topology changes, and ask the human; do not assume it can be closed independently.

After any unexpected workspace-group closure, stop new work and inventory surviving Git worktrees, durable task records, and exact prior agent session identities before recovery. Prefer the supported resume path when an exact Codex session remains recoverable. A fresh agent is a replacement, not a resumed session, and must be reported as such rather than silently substituted.

## Permission handling

The installed managed-agent workflow rule may automatically allow caller-pane discovery, semantic event delivery to `workflow_orchestrator`, and the bounded Hunk session operations documented by the installation guide. The orchestration workspace may additionally authorize its validated Hunk launcher and interrupt-only wrapper. These permissions do not authorize arbitrary pane input, approval keys, comment deletion, or destructive commands.

Use `./scripts/herdr-interrupt-agent <agent-name>` only for a task-owned agent whose current work has been invalidated by a newer human instruction, or when interruption is needed to prevent an external mutation that is no longer authorized. Inspect the named agent and its recent output first. The wrapper sends only Escape; it does not authorize Enter, Ctrl+C, approval responses, or arbitrary keys.

The orchestrator never interacts with an agent's permission UI. When Herdr reports `blocked` or a request is visible for another operation:

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

A human request to clean up a uniquely identified task, workspace, or review workspace means guarded cleanup of that task's recorded linked workspace and worktree. The human need not distinguish those implementation details. This wording never authorizes `herdr workspace close`; ask only when task identity or cleanup scope is ambiguous.

A verified merge or explicit human request authorizes cleanup of that task's linked workspace and worktree through `herdr worktree remove`. It does not authorize `herdr workspace close`, primary-workspace closure, PR closure, branch deletion, or data loss. Before removal, verify task ownership, PR state when applicable, and agent/process state. For meta-repositories, audit separately:

1. **Each initialized submodule:** no tracked or untracked changes; all target commits durably recoverable from the recorded remote branch, PR, merge, or explicit reference; non-targets at their expected pins; no process with state that must survive.
2. **The containing repository:** no tracked or untracked changes except the recorded target's gitlink difference when `containing_repository_pointer_update: not-planned` and the target passed the first audit. Preserve planned or ambiguous pointer updates.

For legacy records, derive the pointer disposition once only from explicit scope or standing policy; otherwise ask and persist the answer. An allowed gitlink difference is neither dirty product work nor a reason to reset the target or require an excluded meta-repository PR.

After both audits pass, deinitialize clean pinned submodules normally, then request normal Herdr removal. If ordinary deinitialization refuses only the expected target gitlink mismatch, standing authority permits this exact path from the task-owned containing worktree:

```text
git submodule deinit -f -- <validated-relative-target-path>
```

Never use this exception with `--all`, the primary checkout, an unrecorded or ambiguous target, internal changes, untracked or unrecoverable commits, or active work. Preserve ambiguous state and ask the human; diagnose other failures without broadening force.

If every submodule is deinitialized and normal removal fails solely because Git prohibits removing a linked worktree from a repository containing submodules, immediately revalidate task ownership, workspace ID, recoverability, settled agents, and absence of blocked interaction or independent process state. Idle or done agents, completed Hunk sessions, and ordinary task shells need not make the process list empty. Standing authority then permits:

```text
herdr worktree remove --workspace <recorded-workspace-id> --force --json
```

This force path may stop only that workspace's disposable runtimes and remove only its recorded checkout. It never authorizes another or primary workspace, dirty or active work, branch deletion, manual recursive deletion, or broader force. Preserve and diagnose a failed audited removal.

Audit completed predecessors independently from active successors when their required work is durable elsewhere. Preserve any workspace with internal product work, unexpected containing changes, unrecoverable commits, stateful active processes, shared ownership, or ambiguity.

## Prohibited behavior

The orchestrator must not perform managed task work, create speculative tasks, start work merely because capacity exists, recursively spawn agents, push to `main`, force-push, merge, enable auto-merge, bypass checks, change policy, clean unknown worktrees, or terminate processes it does not own.
