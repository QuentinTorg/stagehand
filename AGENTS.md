# Orchestration Workspace Instructions

## Purpose and role

This checkout is both the source package and a valid private control workspace for Herdr-managed tasks. Product implementation belongs in task-specific Herdr worktrees, never in this checkout.

The human designates the orchestrator by asking an existing agent to coordinate work. That agent must load and use the repository-local `orchestrating-development` skill before coordinating. Merely running here does not grant the role: maintenance, documentation, and skill-development agents must not bind themselves as controller or consume its wakes.

If a required skill, local configuration, rule, or tool is missing or misconfigured, follow the [guided installation procedure](./skills/orchestrating-development/references/installation.md#guided-setup) before coordinating work.

Before coordinating work, the orchestrator must:

1. inspect the saved controller binding and live Herdr agents; reuse the bound session or obtain human authorization for a handover;
2. load and follow the repository-local `orchestrating-development` skill; and
3. load the local configuration described below.

The [installation procedure](./skills/orchestrating-development/references/installation.md#controller-binding) binds the exact controller session. Names such as `workflow_orchestrator` are optional labels, not routing or ownership requirements. If prerequisites or controller identity remain unresolved, tell the human rather than guessing or replacing an owner.

## Local configuration

Machine-specific paths, repository identities, GitHub hosts, initialization procedures, model choices, and personal policy belong in `.local/AGENTS.md`. Before inspecting or provisioning a managed task, read that file completely and treat it as the workspace configuration consumed by the orchestration skill.

The local file is additive configuration, not another copy of the generic workflow. It may specialize choices that the skill explicitly delegates to workspace policy, but it must not silently weaken the skill's safety or authority boundaries. If the files conflict or the local instruction is ambiguous, preserve state and ask the human.

Do not send this file or the complete local configuration to managed agents. Give each role only the bounded task facts it needs; agents discover and follow the instructions in their own worktree.

Use [`templates/AGENTS.local.md`](./templates/AGENTS.local.md) to create `.local/AGENTS.md`. The local file may instead be a symbolic link to a private configuration repository. Never store credentials or secret values in either form.

## Package and runtime boundaries

- `skills/`, `plugins/`, `scripts/`, `docs/`, and packaged rules are portable source.
- `AGENTS.md` is the portable workspace bootstrap contract.
- `.local/` contains private machine and user configuration and is not versioned here.
- `.orchestrator/` contains mutable task records and scratch state and is not versioned here.
- Bundled agent integration files are tracked; private skill links and permission settings are installation-specific. Their paths and setup belong in the applicable [installation reference](./skills/orchestrating-development/references/installation.md#agent-specific-setup), not in the shared workflow.

The `orchestrating-development` skill owns the generic lifecycle, role contracts, status format, review-loop controls, permission boundaries, and cleanup procedure. Keep environment facts and genuine user choices in the local overlay instead of duplicating the skill.
