# Stagehand

This package helps one developer coordinate coding agents without replacing ordinary team practices. It supports reviewed development, review of existing pull requests, bounded delegated work, and workspace-only exploration.

[Herdr](https://github.com/ogulcancelik/herdr) supplies workspaces, worktrees, panes, and agent lifecycle management. [Hunk](https://github.com/modem-dev/hunk) provides the private local review surface. GitHub draft pull requests preserve intent and become the final handoff to human teammates and CI.

## Intended workflow

1. Ask the orchestrator to start an authorized task or review an existing pull request.
2. The orchestrator creates one Herdr workspace and worktree for that task.
3. Discuss implementation details with the author and approve its plan before editing begins.
4. The author implements, verifies, and creates a draft pull request that records intent.
5. The orchestrator splits the `agents` tab into side-by-side author and reviewer panes, then starts a non-watching Hunk session in its own full-width `hunk` tab.
6. The same author and reviewer repeat the review-and-fix loop for selected in-scope findings.
7. After a passing review, the orchestrator asks whether the reviewer may finalize the pull request.
8. The human and their teammates perform final GitHub review; the human merges through GitHub.

Agents notify the orchestrator through small Herdr workflow events. The orchestrator validates those events against durable task records instead of inferring progress from terminal activity. It does not implement product code, approve unexpected permissions, or merge pull requests.

For investigation, diagnosis, planning, or research with no intended landed change, request a delegated-work task. Stagehand starts one worker in an isolated workspace and returns its result without creating a PR, reviewer, Hunk session, or review loop.

For open-ended human-directed work, request a workspace-only task. If that work later becomes a pull request, Stagehand keeps the same workspace and agent when safe and promotes it into the development review workflow.

## Skills and responsibilities

The workflow composes focused skills rather than loading one large instruction set into every agent:

| Skill | Source | Used by | Responsibility |
| --- | --- | --- | --- |
| `orchestrating-development` | Bundled with Stagehand | Orchestrator | Own task state, Herdr topology, handoffs, limits, and human checkpoints. |
| `preparing-pull-requests` | [SkillDex](https://github.com/QuentinTorg/skilldex) | Author or authorized reviewer | Create the intent-bearing draft or finalize an approved reviewed head. |
| `reviewing-code` | [SkillDex](https://github.com/QuentinTorg/skilldex) | Reviewer | Perform an independent phased review of the complete changeset. |
| `resolving-findings` | [SkillDex](https://github.com/QuentinTorg/skilldex) | Original author | Resolve only selected in-scope findings and return the change for rereview. |
| `hunk-review` | [Hunk](https://github.com/modem-dev/hunk) | Reviewer | Record and manage private inline feedback in Hunk. |
| `writing-specifications` | [SkillDex](https://github.com/QuentinTorg/skilldex) | Human and author, when useful | Develop architectural intent before implementation; it is not required for every change. |

Stagehand does not vendor the SkillDex or Hunk skills. Install their skill directories individually so agents in product worktrees can discover them; do not link either repository's entire skills directory. This package owns `orchestrating-development` and its Herdr integration, which remain local to the dedicated control workspace so product agents do not assume the orchestrator role.

## Quick setup

Prerequisites:

- Codex, Git, `jq`, and GitHub CLI authentication;
- Herdr installed and running;
- Hunk installed; and
- a SkillDex checkout containing `preparing-pull-requests`, `reviewing-code`, and `resolving-findings`; `writing-specifications` is optional.

Then:

1. Clone this package as a dedicated control workspace. Product code and feature worktrees belong elsewhere.
2. Copy [`templates/AGENTS.local.md`](./templates/AGENTS.local.md) to the ignored `.local/AGENTS.md`, then add allowed repository locations, GitHub hosts, initialization requirements, workload preferences, and local policy. Alternatively, make that ignored path a symbolic link to a private configuration repository.
3. Leave the tracked [`AGENTS.md`](./AGENTS.md) generic; it activates orchestration and requires the local overlay without exposing it.
4. Keep the tracked repository-local `orchestrating-development` skill link and Herdr rule in place, and link the separately installed Herdr skill into this workspace's `.codex/skills/` directory.
5. Install the packaged managed-agent workflow rule into `~/.codex/rules/` as an individual symbolic link; unlike the workspace rule, it permits authors and reviewers in product worktrees to deliver bounded events and use Hunk session controls.
6. Install the individual [managed-role skills](./skills/orchestrating-development/references/installation.md#managed-role-skills) from SkillDex and Hunk for agents launched in product worktrees.
7. Restart Codex after adding or changing rules.
8. Check that no other live agent owns the reserved name, then start the single active orchestration controller as `workflow_orchestrator`. Maintenance agents in this repository must use another name or remain unnamed.

Exact commands and policy validation are in the [installation guide](./skills/orchestrating-development/references/installation.md).

The public checkout may serve directly as the live control workspace. `.local/`, `.orchestrator/`, and installation-specific Codex entries are ignored, while the portable orchestration skill link and workspace Herdr rule are tracked.

Start with a natural request such as:

```text
Create a workspace for issue #42. Start an author that explores the repository
and proposes a plan to me, but do not allow implementation before I approve it.
```

Continue implementation discussion in the author pane. Return to the orchestrator for status, finding disposition, finalization authorization, cleanup, or another explicitly authorized task.

Every orchestrator response ends with a compact four-column dashboard of all open tasks: workspace or work item, stage, active roles, and pull request. Provisioned tasks lead with the exact Herdr sidebar workspace label, while repository, issue, and pull-request links remain secondary context. Red, yellow, and green indicators distinguish human-blocked work, active or dependency-blocked workflow, and completed orchestration handoffs. Routine CI and dependency waits remain internal; the final `Needs your attention` section is the single action queue and uses the same workspace labels so the human can immediately find each task in Herdr.

Managed roles report completed handoffs and diagnosed blockers through exact semantic events. They verify Herdr delivery and leave a transcript fallback if it fails. On each monitoring turn, the orchestrator compares its task records with relevant Herdr and durable artifact evidence. When human authority and every intervening boundary are proven, it catches the record up directly to the furthest proven state; otherwise it requests one current-boundary event or returns one focused ambiguity to the human.

## Guardrails

The human explicitly authorizes every task and decides how many workflows run concurrently. Each task owns one workspace and worktree. Development uses a persistent author and reviewer; reviewer-only work uses one reviewer; delegated work uses one worker and cannot silently become implementation; workspace-only work has no managed role until promotion. The orchestrator warns about likely overlap and recommends sequencing, but fixed global concurrency caps are not imposed. Review rounds and material scope revisions remain bounded; unexpected permissions, stale heads, conflicts, and no-progress loops return to the human.

GitHub remains the collaboration boundary. The workflow never pushes to the primary branch, bypasses CI, enables auto-merge, or performs the final merge.

## More detail

- [Design principles](./docs/design/01-design-principles.md)
- [Skill composition](./docs/design/02-skill-composition.md)
- [Orchestration skill](./skills/orchestrating-development/SKILL.md)
- [Orchestration skill specification](./skills/.specs/orchestrating-development-spec.md)
- [Workflow state and events](./skills/orchestrating-development/references/workflow-state.md)
- [Safety and escalation](./skills/orchestrating-development/references/safety-and-escalation.md)
