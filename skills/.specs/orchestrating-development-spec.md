# Orchestration Skill Design Contract

Stagehand is a personal, team-compatible coordinator, not an autonomous product builder. It preserves human intent and delegates engineering methods to the [Skilldex composition](../../docs/design/02-skill-composition.md).

## Responsibilities

- The human selects tasks, approves implementation plans and material scope changes, authorizes reviewer finalization or external review publication, and merges in GitHub.
- The coordinator owns task/workspace identities, handoffs, persistent watch registrations, recoverable progress, finite review budgets, and actionable human status.
- Persistent authors and independent reviewers own implementation and review. They use normal conversation and existing Skilldex skills, not a Stagehand worker protocol.
- The relay provides bounded, durable wake delivery; the board provides presentation. Neither infers semantic success or grants authority.
- Local configuration owns machine paths, repository preparation/cleanup caveats, and explicit model choices.

## Simplification boundaries

Remove infrastructure from worker context: no JSON events, callback commands, control blocks, acknowledgment gates, mandatory Hunk sessions, or separate draft-dispatch turn. Keep intent-bearing drafts before review, exact-head review evidence, selected in-scope fixes, and human-authorized finalization.

Short instructions do not weaken ownership or recoverability. Preserve canonical primary workspaces, initialized-submodule targeting, audited cleanup, native-session recovery, and same-purpose workspace reuse. Direct human scope changes are effective immediately; coordinator bookkeeping catches up rather than blocking them.

Choose smaller agents for bounded work and stronger agents for difficult reasoning under local policy. Cost controls limit unproductive iteration, not the user's authorized number of tasks.

## Sources of detail

The [skill](../orchestrating-development/SKILL.md) owns operational behavior and routes to state, selection, safety, and installation references. Its assets are short assignment examples and coordinator-owned record templates. Do not duplicate those procedures here.

[Design principles](../../docs/design/01-design-principles.md) preserve rationale. [Acceptance scenarios](../orchestrating-development/evals/evals.md) check observable behavior; relay and board unit tests exercise deterministic infrastructure. Tests must distinguish runtime settlement from actual authorization, review outcomes, and current changeset evidence.
