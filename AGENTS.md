# Orchestration Workspace Instructions

## Purpose and role

This checkout is both the source package and a valid private control workspace for Herdr-managed tasks. Product implementation belongs in task-specific Herdr worktrees, never in this checkout.

Exactly one live agent may own the stable Herdr name `workflow_orchestrator`. That named agent is the active workflow orchestrator. Merely running in this repository does not grant the role: maintenance, documentation, and skill-development agents must remain unnamed or use another name and must not consume managed-agent events.

An agent launched as `workflow_orchestrator` must load and use the repository-local `orchestrating-development` skill before handling its first request.

If a required skill, local configuration, rule, or tool is missing or misconfigured, follow the [guided installation procedure](./skills/orchestrating-development/references/installation.md#guided-setup) before coordinating work.

An unnamed agent asked to orchestrate must load the orchestration skill and inspect live agents. If `workflow_orchestrator` is unowned, name the current agent with `herdr agent rename <current-pane-id> workflow_orchestrator` before reading task state; otherwise reuse the owner or ask the human.

Before coordinating work, the named orchestrator must:

1. inspect live Herdr agents and reuse the intended `workflow_orchestrator` owner when one exists;
2. load and follow the repository-local `orchestrating-development` skill; and
3. load the local configuration described below.

After controller activation or session resume, detected or suspected context compaction, or uncertainty about prior state, do not coordinate from the conversation summary. Before the first mutation, reread the complete local configuration, orchestration skill, its project-control, workflow-state, and safety references, current project/package/task records, applicable decisions, and the authoritative product sections cited by active or next-candidate packages. Reconcile live evidence and persist the project rehydration checkpoint. Autonomous projects must also enforce the checkpoint's deterministic full-rehydration interval even when compaction is not detectable. Consequential transitions require a narrow validation of their exact package, repository, head, evidence, and cited product sections; they do not independently force another full rehydration while the checkpoint remains current.

If a prerequisite remains unresolved after guided setup, or ownership of the reserved name is ambiguous, stop and tell the human instead of improvising or replacing an active owner.

## Local configuration

Machine-specific paths, repository identities, GitHub hosts, initialization procedures, model choices, and personal policy belong in `.local/AGENTS.md`. The machine-readable canonical task-record root belongs in `.local/workspace.yaml`. Before inspecting or provisioning a managed task, read both files completely and treat them as the workspace configuration consumed by the orchestration skill.

The local file is additive configuration, not another copy of the generic workflow. It may specialize choices that the skill explicitly delegates to workspace policy, but it must not silently weaken the skill's safety or authority boundaries. If the files conflict or the local instruction is ambiguous, preserve state and ask the human.

Do not send this file or the complete local configuration to managed agents. Give each role only the bounded task facts it needs; agents discover and follow the instructions in their own worktree.

Use [`templates/AGENTS.local.md`](./templates/AGENTS.local.md) to create `.local/AGENTS.md` and [`skills/orchestrating-development/assets/workspace-config.yaml`](./skills/orchestrating-development/assets/workspace-config.yaml) to create `.local/workspace.yaml`. Either local file may instead be a symbolic link to a private configuration repository. Never store credentials or secret values in either form.

## Package and runtime boundaries

- `skills/`, `scripts/`, `docs/`, and packaged rules are portable source.
- `AGENTS.md` is the portable workspace bootstrap contract.
- `.local/` contains private machine and user configuration and is not versioned here.
- `.orchestrator/` contains mutable task records and scratch state and is not versioned here.
- `.codex/skills/orchestrating-development` is a tracked relative link to the bundled skill; other skill links are installation-specific and not versioned here.
- `.codex/rules/herdr.rules` is the tracked workspace policy for orchestrator-side Herdr operations; other workspace rules are local and not versioned here.

The `orchestrating-development` skill owns the generic lifecycle, authority profiles, autonomous-project controls, role contracts, status format, review-loop controls, guarded integration procedure, permission boundaries, and cleanup procedure. Keep environment facts, project charters, and genuine user choices in the local overlay and mutable orchestration records instead of duplicating them in portable instructions.

An autonomous project does not weaken repository boundaries. Its orchestrator may approve package plans, resolve in-charter specification decisions, and squash-merge reviewed work only into integration branches explicitly named by its active charter. Managed product roles never gain shared-branch merge authority, and no agent may implement on, push to, or merge into `main` under an autonomous charter.
