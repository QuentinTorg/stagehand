# Orchestration Workspace Instructions

## Purpose and role

This checkout is both the source package and a valid private control workspace for Herdr-managed development. Product implementation belongs in task-specific Herdr worktrees, never in this checkout.

Exactly one live agent may own the stable Herdr name `workflow_orchestrator`. That named agent is the active workflow orchestrator. Merely running in this repository does not grant the role: maintenance, documentation, and skill-development agents must remain unnamed or use another name and must not consume managed-agent events.

Before coordinating work, the named orchestrator must:

1. inspect live Herdr agents and reuse the intended `workflow_orchestrator` owner when one exists;
2. load and follow the repository-local `orchestrating-development` skill; and
3. load the local configuration described below.

If the skill is unavailable, the local configuration is missing, or ownership of the reserved name is ambiguous, stop and tell the human instead of improvising or replacing an active owner.

## Local configuration

Machine-specific paths, repository identities, GitHub hosts, initialization procedures, model choices, and personal policy belong in `.local/AGENTS.md`. Before inspecting or provisioning a managed task, read that file completely and treat it as the workspace configuration consumed by the orchestration skill.

The local file is additive configuration, not another copy of the generic workflow. It may specialize choices that the skill explicitly delegates to workspace policy, but it must not silently weaken the skill's safety or authority boundaries. If the files conflict or the local instruction is ambiguous, preserve state and ask the human.

Do not send this file or the complete local configuration to managed product agents. Give each role only the bounded task facts it needs; product agents discover and follow the instructions in their own worktree.

Use [`templates/AGENTS.local.md`](./templates/AGENTS.local.md) to create `.local/AGENTS.md`. The local file may instead be a symbolic link to a private configuration repository. Never store credentials or secret values in either form.

## Package and runtime boundaries

- `skills/`, `scripts/`, `docs/`, and packaged rules are portable source.
- `AGENTS.md` is the portable workspace bootstrap contract.
- `.local/` contains private machine and user configuration and is not versioned here.
- `.orchestrator/` contains mutable task records and scratch state and is not versioned here.
- `.codex/skills/orchestrating-development` is a tracked relative link to the bundled skill; other skill links are installation-specific and not versioned here.
- `.codex/rules/herdr.rules` is the tracked workspace policy for orchestrator-side Herdr operations; other workspace rules are local and not versioned here.

The `orchestrating-development` skill owns the generic lifecycle, role contracts, status format, review-loop controls, permission boundaries, and cleanup procedure. Keep environment facts and genuine user choices in the local overlay instead of duplicating the skill.
