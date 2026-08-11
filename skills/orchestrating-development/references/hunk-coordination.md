# Hunk Coordination

## Topology and launch

Use this fixed topology for every development task:

- one Herdr workspace for the task;
- an `agents` tab containing the author pane on the left and reviewer pane on the right, side-by-side across a vertical divider; and
- a separate `hunk` tab containing one unsplit, full-width Hunk pane.

The author starts alone in the `agents` tab. When review begins, split the author pane toward the right and start the reviewer in the new right-hand pane; do not create a separate reviewer tab. Create the `hunk` tab separately with `--cwd` set to the task record's exact development-target path and do not split it. For a submodule pull request this is the submodule checkout, not its containing worktree root. Preserve this layout across fix and rereview rounds instead of creating replacement panes or tabs.

Each task workspace contains one Hunk pane rooted in the repository that owns the pull-request comparison. Do not share a Hunk session across tasks. Immediately after tab creation, inspect the returned root pane and require its cwd to equal the recorded development target before launch. Launch Hunk with a normal review command and never enable watch mode for this workflow.

From the orchestration workspace, launch a committed base-to-head comparison with `./scripts/herdr-hunk-diff <pane-id> <base-ref> [head-ref]`. The validated wrapper confirms that the pane cwd is a Git worktree containing both comparison commits before starting Hunk. It is the approved boundary for launch; do not replace it with unrestricted `herdr pane run` authority.

If cwd validation fails, do not use `herdr pane run ... cd`, `send-text`, or `send-keys` to repair the shell. Those primitives can execute arbitrary input and correctly retain a human checkpoint. Stop review setup and recreate the task-owned Hunk tab with the exact development-target `--cwd`; if replacing the mistaken tab requires an otherwise gated close operation, surface that narrow cleanup decision rather than requesting broad terminal authority.

Choose the comparison from the task record and draft pull request. For a committed Git branch this is normally the pull request's base-to-head comparison, not an incidental working-tree diff. If the branch contains relevant uncommitted changes, reconcile them before claiming the pull request head is ready for review.

After launch, use the installed Hunk skill to inspect the session's repository and source. Verify both before giving the reviewer its session identity. Do not assume that the visually focused Hunk window belongs to the current task.

## Review and resolution order

1. Load or reload the intended current base-to-head changeset.
2. Give the reviewer the verified Hunk session and changeset identity.
3. Let the reviewer add material inline findings and emit its semantic outcome.
4. Obtain the selected current-change finding set under the configured human-disposition policy.
5. Prompt the original author to consume those comments and resolve the selected set.
6. Keep the Hunk session unchanged while the author edits so existing comments remain available.
7. Accept `fixes-ready` only after validating the new branch and pull-request head.
8. Preserve the review outcome in the task record, then explicitly reload Hunk against the same base and new head.
9. Ask the same reviewer for a complete rereview.

Reload may clear or invalidate previous agent comments. That is expected only after the author has consumed them and their normalized outcome has been recorded. Never reload merely because filesystem changes appeared.

## Base and identity checks

Before every review round, confirm:

- Hunk's repository is the recorded development target that owns the pull request;
- the base matches the pull request's intended base;
- the displayed head matches the event and current PR head;
- the scope version and review round match the task record; and
- untracked or dirty files are either intentionally included or explicitly excluded from the review claim.

Delegate live-session commands, navigation, comments, and reload syntax to the installed Hunk skill. The orchestration skill owns when and why to use those operations, not their CLI details.

## Failure and recovery

If Hunk closes or the session cannot be resolved, do not discard the reviewer outcome. Recreate one non-watching session in the task workspace, validate its source, and repopulate only still-current findings when needed.

Hunk comments are private transport state. Product intent remains in the task brief and pull request; review status remains in the semantic event and task record. Do not treat a missing comment, closed session, or empty refreshed diff as proof that a finding was resolved.
