# Installation

The checkout already tracks a relative `.codex/skills/orchestrating-development` link to its bundled skill and a `.codex/rules/herdr.rules` policy for orchestrator-side Herdr operations. Keep both in place. Install the external Herdr skill only in the dedicated orchestration workspace. Separately install the managed-agent workflow rule in the user rules directory so authors and reviewers launched from product worktrees can identify their pane, notify the orchestrator, and use the bounded Hunk session API. Use individual symbolic links; do not link a parent `skills` or source-repository directory.

## Guided setup

When asked to check or prepare Stagehand, inspect the current installation before changing it. Report what is ready, what is missing or misconfigured, and any value the human must supply. Then preview the remaining work in order, naming each exact source and destination and whether it will be copied, linked, configured, validated, or require a Codex restart. Use the procedures below rather than inventing another installation method.

Do not stop after listing missing components. If the user requested only an audit, offer to apply the proposed setup. If the user requested setup, carry out the previewed actions within that authorization and pause only for an unresolved choice, unsafe existing destination, credential interaction, or required external permission. Never replace an existing file or link without first showing what owns it and where it points.

Afterward, validate every installed link and rule, distinguish completed setup from remaining human actions, and state whether existing Codex sessions must restart.

Keep the tracked root `AGENTS.md` generic. Create the ignored local configuration before starting an orchestrator:

```sh
mkdir -p /path/to/orchestration-workspace/.local
cp /path/to/orchestration-workspace/templates/AGENTS.local.md \
  /path/to/orchestration-workspace/.local/AGENTS.md
cp /path/to/orchestration-workspace/skills/orchestrating-development/assets/workspace-config.yaml \
  /path/to/orchestration-workspace/.local/workspace.yaml
```

Customize the Markdown file with repository paths, hosts, initialization policy, and user preferences. Set the YAML file's `task_records_directory` to the absolute canonical mutable-task directory and `trusted_command_path` to absolute tool directories outside every managed task worktree. Either may instead be an individual symbolic link to a file in a private configuration repository. Do not commit local files or put credentials in them. If either local file is missing or invalid, orchestration activation must stop while package maintenance and setup remain available.

Before adding other files, confirm that Git ignores the local configuration:

```sh
git check-ignore .local/AGENTS.md
git check-ignore .local/workspace.yaml
```

The command must identify a repository ignore rule. Stop and repair `.gitignore` if it does not.

The orchestration host must provide Git, `jq`, Ruby with its standard YAML library, and standard POSIX utilities. The validated Hunk launcher uses `jq` to verify the target pane's Herdr-reported working directory. The guarded project merge and task-branch publication scripts use Ruby only to parse local YAML records and `jq` to validate structured responses.

`herdr --skill` prints guidance matching the installed Herdr version. During guided setup, use it when the Herdr skill is not yet discoverable; a workspace-local link remains preferred for automatic skill routing.

```sh
mkdir -p /path/to/orchestration-workspace/.codex/skills ~/.codex/rules
ln -s /absolute/path/to/herdr-skill \
  /path/to/orchestration-workspace/.codex/skills/herdr
ln -s /absolute/path/to/orchestration-workspace/skills/orchestrating-development/assets/codex-managed-agent-events.rules \
  ~/.codex/rules/orchestrating-development-events.rules
ln -s /absolute/path/to/orchestration-workspace/scripts/managed-task-branch-push \
  ~/.local/bin/stagehand-managed-task-branch-push
```

Replace the example paths with the actual orchestration workspace and Herdr skill locations. Refuse to replace a destination when it already exists until its ownership and target have been inspected. Do not replace the tracked orchestration link or install `orchestrating-development` globally; its repository-local placement prevents product agents from assuming the orchestrator role.

The rule files have different consumers and installation scopes:

- `.codex/rules/herdr.rules` is tracked in this workspace and grants the orchestrator bounded Herdr inspection and task-management operations.
- `assets/codex-managed-agent-events.rules` is linked into `~/.codex/rules/` and grants managed authors and reviewers only event delivery, caller-pane discovery, and bounded Hunk operations.
- `assets/codex-managed-role.rules` is installed only into each managed task worktree before its agent starts. It forbids direct publication there and allows the record-aware task-branch guard. Never install it globally, because unrelated Codex sessions retain their own Git policy.

Before starting any managed author or reviewer, install and validate its worktree-local boundary:

```sh
/absolute/path/to/orchestration-workspace/scripts/install-managed-role-boundary \
  /absolute/path/to/complete-managed-worktree
codex execpolicy check \
  --rules /absolute/path/to/complete-managed-worktree/.codex/rules/stagehand-managed-role.rules \
  --pretty git push --force origin main
codex execpolicy check \
  --rules /absolute/path/to/complete-managed-worktree/.codex/rules/stagehand-managed-role.rules \
  --pretty stagehand-managed-task-branch-push \
  --task-record /absolute/path/to/orchestration-workspace/.orchestrator/tasks/example.yaml \
  --expected-head 0123456789012345678901234567890123456789
```

The first result must be `forbidden` and the second `allow`. The guarded command may add `--create-draft-pr --title <title> --body <body>` only while the canonical task record authorizes initial draft creation; it creates the PR from the explicit already-pushed task head against the recorded non-main integration branch. The installer adds only the exact rule path to the worktree-specific Git exclude file, so runtime policy cannot leak into a product changeset. Do not start the role if the destination already exists with another owner or target. Codex loads workspace rules at startup; installing the boundary afterward is not sufficient.

Start managed Codex roles with `--sandbox workspace-write --ask-for-approval never` after installing the rule. The non-escalating approval policy is part of the publication boundary: alternate executable paths, environment launchers, and Git global-option forms that do not match an explicit denial remain sandboxed and cannot obtain network authority. Do not add `--approve-for-me`, a permissive approval policy, an extra writable credential/helper directory, or a network-enabling override. Commands explicitly allowed by the task-worktree and user rules remain available for the guarded publisher, workflow events, Hunk, and preauthorized build/test operations.

## Managed-role skills

Stagehand does not vendor its managed-role skills. Clone [SkillDex](https://github.com/QuentinTorg/skilldex) and [Hunk](https://github.com/modem-dev/hunk), then install the required skill directories individually where product-worktree agents can discover them:

```sh
mkdir -p ~/.codex/skills
ln -s /absolute/path/to/skilldex/skills/preparing-pull-requests ~/.codex/skills/preparing-pull-requests
ln -s /absolute/path/to/skilldex/skills/resolving-findings ~/.codex/skills/resolving-findings
ln -s /absolute/path/to/skilldex/skills/reviewing-code ~/.codex/skills/reviewing-code
ln -s /absolute/path/to/hunk/skills/hunk-review ~/.codex/skills/hunk-review
```

The SkillDex `writing-specifications` skill is optional for changes that benefit from architectural design before authoring:

```sh
ln -s /absolute/path/to/skilldex/skills/writing-specifications ~/.codex/skills/writing-specifications
```

Refuse to replace an existing destination before inspecting it. Do not install superseded feedback or review skills merely because they share the same source repository.

Reserve the Herdr name `workflow_orchestrator` for exactly one live orchestration agent. Before starting or naming it, run `herdr agent list` and inspect any existing owner. Reuse the intended live owner. If the name belongs to a stale, maintenance, or ambiguous session, inspect its pane, session identity, recent output, and active task records; obtain human direction before clearing or reassigning the name. Do not work around a collision by teaching managed agents a pane ID because pane IDs are session-local transport details rather than the stable endpoint.

Only the active orchestration controller owns the reserved name. Other agents may work in the orchestration repository for documentation, package maintenance, or skill development, but remain unnamed or use a different non-reserved name and must not consume workflow events. The installed rule allows managed agents to deliver `herdr agent prompt workflow_orchestrator ...` notifications and use Hunk inspection, navigation, reload, and finding-recording commands. It does not grant permission to launch Hunk directly, delete Hunk comments, start agents, control arbitrary panes, send keys, or modify workspaces.

Restart Codex sessions after installing or changing the rule; rules are loaded at startup. Existing managed sessions may require one manual approval for a prompt already waiting in their terminal.

Validate the installed rule before starting a managed task:

```sh
codex execpolicy check --rules ~/.codex/rules/orchestrating-development-events.rules \
  --pretty herdr agent prompt workflow_orchestrator workflow-event
```

The result must be `allow`. A prompt to another agent and `herdr agent send-keys` must remain unmatched.

Also validate caller-context discovery:

```sh
codex execpolicy check --rules ~/.codex/rules/orchestrating-development-events.rules \
  --pretty herdr pane current --current
```

Validate the Hunk session boundary as well:

```sh
codex execpolicy check --rules ~/.codex/rules/orchestrating-development-events.rules \
  --pretty hunk session review session-123 --json
codex execpolicy check --rules ~/.codex/rules/orchestrating-development-events.rules \
  --pretty hunk session comment clear session-123 --all --yes
```

The review command must be `allow`; destructive comment clearing must remain unmatched.

For autonomous-project installations, validate the global privilege and merge denials:

```sh
codex execpolicy check --rules ~/.codex/rules/orchestrating-development-events.rules \
  --pretty gh pr merge 42 --squash
codex execpolicy check --rules ~/.codex/rules/orchestrating-development-events.rules \
  --pretty sudo ip link add stagehand-test0 type dummy
```

Both commands must be `forbidden`. Then run `./scripts/test-project-squash-merge` and `./scripts/test-managed-task-branch-push` from the Stagehand checkout. Both must pass before the charter grants autonomous publication or merge authority.
