# Stagehand

This package helps one developer coordinate coding agents without replacing ordinary team practices. It supports reviewed development, review of existing pull requests, bounded delegated work, and workspace-only exploration.

[Herdr](https://github.com/ogulcancelik/herdr) supplies workspaces, worktrees, panes, and agent lifecycle management. GitHub draft pull requests preserve intent and become the final handoff to human teammates and CI.

The workflow is agent-neutral. Configure instruction/skill discovery and permissions for your selected Herdr-supported agents; choose agents and models in local configuration.

## Intended workflow

1. Ask the orchestrator to start an authorized task or review an existing pull request.
2. The orchestrator creates one Herdr workspace and worktree for that task.
3. Discuss implementation details with the author and approve its plan before editing begins.
4. The author implements, verifies, and creates a draft pull request that records intent.
5. The orchestrator adds an independent reviewer, by default beside the author in the task's `agents` tab.
6. The same author and reviewer repeat the review-and-fix loop for selected in-scope findings.
7. After a passing review, the orchestrator asks whether the reviewer may finalize the pull request.
8. The human and their teammates perform final GitHub review; the human merges through GitHub.

Workers answer normally. A bundled plugin watches their turns—including direct human conversations—and wakes the coordinator to inspect results and update task state. Workers need no callbacks, JSON, or orchestration instructions. It does not implement product code, approve unexpected permissions, or merge pull requests.

For investigation, diagnosis, planning, or research with no intended landed change, request a delegated-work task. Stagehand starts one worker in an isolated workspace and returns its result without creating a PR, reviewer, or review loop.

For open-ended human-directed work, request a workspace-only task. If that work later becomes a pull request, Stagehand keeps the same workspace and agent when safe and promotes it into the development review workflow.

## Skills and responsibilities

The workflow composes focused skills rather than loading one large instruction set into every agent:

| Skill | Source | Used by | Responsibility |
| --- | --- | --- | --- |
| `orchestrating-development` | Bundled with Stagehand | Orchestrator | Own task state, Herdr topology, handoffs, limits, and human checkpoints. |
| `preparing-pull-requests` | [SkillDex](https://github.com/QuentinTorg/skilldex) | Author or authorized reviewer | Create the intent-bearing draft or finalize an approved reviewed head. |
| `reviewing-code` | [SkillDex](https://github.com/QuentinTorg/skilldex) | Reviewer | Perform an independent phased review of the complete changeset. |
| `resolving-findings` | [SkillDex](https://github.com/QuentinTorg/skilldex) | Original author | Resolve only selected in-scope findings and return the change for rereview. |
| `writing-specifications` | [SkillDex](https://github.com/QuentinTorg/skilldex) | Human and author, when useful | Develop architectural intent before implementation; it is not required for every change. |

Stagehand does not vendor the SkillDex skills. Hunk is optional and not part of required setup. Install their skill directories individually so agents in product worktrees can discover them; do not link the repository's entire skills directory. This package owns `orchestrating-development` and its Herdr integration, which remain local to the dedicated control workspace so product agents do not assume the orchestrator role.

## Quick setup

You may ask an agent to check or perform setup. It should follow the [guided installation procedure](./skills/orchestrating-development/references/installation.md#guided-setup): identify what is already ready, explain each proposed copy, link, configuration, and validation step, then offer to apply missing setup instead of only reporting it.

Prerequisites:

- A supported coding agent, Git, Python 3, and GitHub CLI authentication;
- Herdr installed and running; and
- a SkillDex checkout containing `preparing-pull-requests`, `reviewing-code`, and `resolving-findings`; `writing-specifications` is optional.

Then:

1. Clone this package as a dedicated control workspace. Product code and feature worktrees belong elsewhere.
2. Copy [`templates/AGENTS.local.md`](./templates/AGENTS.local.md) to the ignored `.local/AGENTS.md`, then add allowed repository locations, GitHub hosts, initialization requirements, workload preferences, and local policy. Alternatively, make that ignored path a symbolic link to a private configuration repository.
3. Leave the tracked [`AGENTS.md`](./AGENTS.md) generic; it activates orchestration and requires the local overlay without exposing it.
4. Configure [workspace instructions and skills](./skills/orchestrating-development/references/installation.md#workspace-and-skills) using only the setup instructions for your selected agents.
5. Link, enable, and configure the bundled [Agent Wake Relay](./skills/orchestrating-development/references/installation.md#agent-wake-relay) for this exact control workspace.
6. Install the individual [managed-role skills](./skills/orchestrating-development/references/installation.md#managed-role-skills) from SkillDex for agents launched in product worktrees. No global worker event rules are needed.
7. Install the optional [status board](./plugins/status-board/README.md#setup), then apply any reload requirements from your agent's setup instructions.
8. Check that no other live agent owns the reserved name, then start the single active orchestration controller as `workflow_orchestrator`. Maintenance agents in this repository must use another name or remain unnamed.

Exact commands and policy validation are in the [installation guide](./skills/orchestrating-development/references/installation.md).

The public checkout may serve directly as the live control workspace. `.local/` and `.orchestrator/` are ignored. Keep private installation settings out of version control; bundled integration files remain tracked.

Start with a natural request such as:

```text
Create a workspace for issue #42. Start an author that explores the repository
and proposes a plan to me, but do not allow implementation before I approve it.
```

Continue implementation discussion in the author pane. Return to the orchestrator for status, finding disposition, finalization authorization, cleanup, or another explicitly authorized task.

Keep the orchestrator conversation and a persistent [status board](./plugins/status-board/README.md) in two panes of the control workspace. The board renders workspace names, current work, next actors, PRs, and live Herdr status. Red, yellow, and green distinguish human-blocked work, ongoing workflow, and completed orchestration handoffs. The orchestrator saves progress as usual and focuses its responses on results and decisions; workers have no new reporting duties. A text dashboard remains available when the board is unavailable or requested.

The coordinator preserves concise outcomes and next actions, then reconciles worker responses with Git/PR evidence. A wake or idle agent is not proof of approval or success. After a missed notification or restart, it catches up without replaying old handoffs or requiring workers to reconstruct events.

## Guardrails

The human explicitly authorizes every task and decides how many workflows run concurrently. Each task owns one workspace and worktree. Development uses a persistent author and reviewer; reviewer-only work uses one reviewer; delegated work uses one worker and cannot silently become implementation; workspace-only work can host a human-directed agent without a delivery loop. The orchestrator warns about likely overlap and recommends sequencing, but fixed concurrency or review-count caps are not imposed. Unexpected permissions, stale heads, material disagreement, broader scope, and repeated non-progress return to the human.

GitHub remains the collaboration boundary. The workflow never pushes to the primary branch, bypasses CI, enables auto-merge, or performs the final merge.

## More detail

- [Design principles](./docs/design/01-design-principles.md)
- [Skill composition](./docs/design/02-skill-composition.md)
- [Orchestration skill](./skills/orchestrating-development/SKILL.md)
- [Orchestration skill specification](./skills/.specs/orchestrating-development-spec.md)
- [State and wakeups](./skills/orchestrating-development/references/workflow-state.md)
- [Safety and escalation](./skills/orchestrating-development/references/safety-and-escalation.md)
