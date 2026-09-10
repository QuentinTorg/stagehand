# Workspace Safety

Read for provisioning, permissions, overlap, or cleanup. The main skill owns workflow authority and review limits; this reference preserves operational caveats.

## Preparation and overlap

Resolve the canonical repository from local configuration or explicit human confirmation. Location roots are hints, not permission to scan every child. Keep private configuration out of worker prompts and public artifacts.

Fetch the intended target base and record its exact commit. Create new work from that commit, not an incidental checkout or meta-repository pin. Preserve a dirty, ahead, diverged, or off-branch primary checkout; fast-forward a clean expected primary only under local policy. Never reset, stash, or discard state to enable synchronization.

Initialize the task worktree according to local repository guidance, then verify the root and target repository, remotes, feature branch, and base before dispatch. Before a submodule is initialized, Git commands inside its directory may act on the parent repository instead. Do remote overrides only after initialization. Non-target submodules stay at their intended pins.

Compare requested work with active tasks for shared contracts, files, generated output, submodule pointers, and build caches. Explain likely conflicts and recommend sequencing; the human may authorize proceeding. Do not create speculative helpers to resolve overlap.

## Herdr worktree groups

Closing a non-linked primary workspace can terminate its entire repository group, including unrelated linked workspaces. Use `herdr worktree create` directly from the verified canonical parent/checkout and record the returned task workspace. Never create a provisional parent or use `herdr workspace close` for task provisioning or cleanup. Do not bypass this through pane/tab closure that would close a parent.

If an accidental duplicate parent appears, preserve it and ask; do not assume it closes independently. After an unexpected group closure, stop topology changes, inventory surviving worktrees and exact session identities, and prefer genuine session resume over silent replacement.

## Permissions and stalled work

Workspace rules allow bounded Herdr operations; task authorization is not a command allowlist. Diagnose the current permission request and explain the needed human action. Never send approval keys, credentials, or arbitrary terminal input on the human's behalf.

The interrupt-only wrapper `./scripts/herdr-interrupt-agent <name>` is for an owned agent whose work was invalidated or whose next external mutation is no longer authorized. Inspect it first; the wrapper sends Escape, not an approval.

Repeated unproductive fixes, incompatible conclusions, unexplained head changes, overlap, or configured review/cost limits need intervention rather than more loops or replacement agents. Model escalation follows [Agent Selection](agent-selection.md). A long build or quiet output is not failure; inspect the owned process and its actual timeout before proposing interruption. Report elapsed time when useful without inventing token measurements.

## Cleanup

A request to clean up a uniquely identified task, workspace, or review workspace authorizes guarded removal of its recorded linked worktree/workspace. A verified merge also makes it eligible. Neither authorizes primary-workspace closure, PR closure, branch deletion, or data loss.

Before removal, verify ownership, exact linked workspace, recoverability, and absence of active work or stateful processes. An idle terminal alone proves none of these. For meta-repositories audit separately:

1. **Initialized submodules:** no internal tracked/untracked changes; target commits durably recoverable through recorded remote branches, PRs, merges, or explicit references; non-targets at expected pins.
2. **Containing repository:** no changes except a recorded target gitlink difference whose pointer update is `not-planned` and whose child passed the first audit. Preserve planned or ambiguous pointer updates.

Derive a legacy pointer policy only from explicit scope or standing local policy. An allowed gitlink difference is not dirty product work and does not require resetting the target or creating an excluded meta PR. Preserve valuable ignored files and process state as well as Git content.

After the audit, deinitialize clean pinned submodules normally and use `herdr worktree remove`. If deinitialization refuses only the expected target gitlink mismatch, standing authority permits this exact operation from the task-owned containing worktree:

```text
git submodule deinit -f -- <validated-relative-target-path>
```

Never use that exception with `--all`, a primary checkout, an ambiguous target, internal changes, unrecoverable commits, or active work.

If submodules are deinitialized and normal removal fails solely because Git prohibits removing a linked worktree from a repository containing submodules, revalidate ownership and recoverability, then use:

```text
herdr worktree remove --workspace <recorded-workspace-id> --force --json
```

This exception may remove only that task's checkout and disposable runtimes. Ordinary settled agents and shells need not make the process list empty. Never broaden it to dirty or active work, another workspace, branch deletion, or manual recursive deletion. Preserve and diagnose other failures.

Audit completed predecessors separately from active successors whose work is durable elsewhere. Cancel the removed task's wake subscriptions and archive its record as described in [State and Wakeups](workflow-state.md); do not keep cleaned tasks in normal status.
