# Skill Specification: orchestrating-development

## 1. Intent

Coordinate Herdr-managed development, reviewer-only, delegated-work, and workspace-only tasks while the human retains task, scope, risk, publication, finalization, and merge authority. Herdr supplies runtime control; this skill supplies durable workflow state, bounded role handoffs, review loops, and recovery.

The operating model is:

- one authorized task per Herdr workspace and worktree, with same-lineage workspace-only work promotable into development;
- one persistent author and reviewer for development, one reviewer for reviewer-only work, one worker for delegated work, or no managed role for workspace-only work until promotion;
- implementation planning between the human and author;
- a draft PR carrying intent before private Hunk review;
- selected findings returned to the original author and completely rereviewed;
- human-authorized PR finalization by the reviewer; and
- final review and merge by humans in GitHub.

This design responds to observed failures: inferred plan approval, missing or misrouted events, stale task records, recursive agents, unbounded review cycles, scope bloat, Hunk watch-mode comment loss, incorrect submodule review roots, noisy dashboards, unsafe workspace cleanup, cascading worktree-group closure, and personal configuration leaking into a portable package. Long-lived orchestrators also need concise, single-owner instructions to preserve context across many tasks.

See [Stagehand design principles](../../docs/design/01-design-principles.md) and [skill composition](../../docs/design/02-skill-composition.md) for product-level rationale.

## 2. Trigger contract

Trigger only when the user explicitly asks an agent in a configured orchestration workspace to become the controller or to start, coordinate, monitor, resume, or report on Herdr-managed development, reviewer-only, bounded delegated work, or workspace-only work. A fresh unnamed controller may claim `workflow_orchestrator` only after confirming that no live owner exists.

Do not trigger for implementation, author planning, direct review, finding resolution, Hunk interaction alone, PR preparation alone, orchestration discussion, or work from a product repository. Repository-local installation aids routing but does not replace the activation checks in `SKILL.md`.

## 3. Behavioral contract

The canonical procedure is [SKILL.md](../orchestrating-development/SKILL.md). Its critical invariants are:

1. Load the workspace configuration chain and version-matched Herdr guidance; never guess repositories, authority, policy, or CLI behavior.
2. Reconcile durable active task records with Herdr and relevant Git, GitHub, verification, and Hunk evidence before mutation; archived records remain outside normal operation.
3. Require explicit task authorization and author-session plan approval. Lifecycle state never proves either.
4. Provision from a verified fetched base with one direct Herdr worktree operation. Preserve primary checkouts and persistent parent workspaces; never create or close a provisional non-linked workspace.
5. Bind every managed-role instruction to task, role, endpoint, scope, stage, and allowed semantic outcomes.
6. Keep author and reviewer roles persistent and independent. Managed roles do not spawn agents.
7. Require the author to create an intent-bearing draft PR before review. The reviewer acquires intent from GitHub context and surrounding code.
8. Keep Hunk non-watching, task-local, rooted in the repository owning the PR, and unchanged until findings are consumed.
9. Return only human-selected material findings to the author. Every changed head receives a complete rereview by the same reviewer.
10. Treat direct human scope changes in the author pane as sufficient authority, synchronize them through a versioned scope update without duplicate approval, and require a new phase-zero review.
11. Require human authorization for reviewer finalization, reviewer-only publication, exceptional permissions, risky actions, budget overrides, and ambiguous cleanup. Reviewer-only publication puts attachable code-specific findings inline and reserves the body for summary and non-attachable findings. Humans always merge.
12. Reconcile missing events to the furthest independently proven state with at most one catch-up request; preserve ambiguity.
13. Report all open tasks with the fixed dashboard and a single human-action section.
14. Interpret ordinary task/workspace cleanup language as guarded removal of the uniquely identified task's recorded linked workspace and worktree, then archive its cleaned record outside the active set; preserve ambiguous targets.
15. Keep delegated work to one worker, two outcomes, and no PR or review loop; landed changes require development authorization.
16. Extend a cohesive existing task and reuse its workspace and roles when safe, including related multi-repository or multi-PR follow-ups; isolate independent or conflicting work.

## 4. Guardrails

- Human authorization, not available capacity, controls parallelism.
- Development has at most one author and reviewer; reviewer-only has one reviewer; delegated work has one worker; workspace-only has no managed role until promotion.
- Default limits are three accepted review outcomes per scope and six total. A third material scope revision requires a progress and cost check.
- Repeated findings, no-progress fixes, conflicting conclusions, missing events, unknown head changes, or overlap trigger escalation rather than another loop.
- Herdr lifecycle proves activity only. Git and GitHub prove artifacts only. Neither proves human authority or reviewer conclusions.
- The orchestrator never implements, reviews, fixes, merges, pushes primary branches, force-pushes, bypasses policy, publishes unapproved reviews, or cleans ambiguous work.
- The orchestrator never invokes `herdr workspace close`; audited task cleanup uses worktree removal on the recorded linked workspace.
- Product agents receive role contracts, not this skill or private orchestration configuration.

## 5. Progressive disclosure

`SKILL.md` owns activation, routing, the end-to-end procedure, and dashboard format. Load specialized details only when applicable:

- [workflow-state.md](../orchestrating-development/references/workflow-state.md): states, events, reconciliation, counters, restart recovery, and cleanup eligibility;
- [agent-contracts.md](../orchestrating-development/references/agent-contracts.md): persistent author, reviewer, and worker behavior;
- [safety-and-escalation.md](../orchestrating-development/references/safety-and-escalation.md): limits, permissions, conflicts, human checkpoints, and cleanup authority;
- [hunk-coordination.md](../orchestrating-development/references/hunk-coordination.md): pane topology, changeset identity, reload order, and recovery;
- [installation.md](../orchestrating-development/references/installation.md): installation only;
- `assets/`: rendered role prompts, event controls, task-record schema, and Codex rules;
- repository scripts: narrowly validated Hunk launch and agent interruption.

Root `AGENTS.md` owns portable workspace policy. Personal repositories, paths, hosts, models, initialization, and stricter limits belong in the ignored local overlay represented by `templates/AGENTS.local.md`. SkillDex supplies complementary author/reviewer skills; Herdr supplies terminal control.

## 6. Evaluation

[Manual acceptance scenarios](../orchestrating-development/evals/evals.md) are the executable contract. Compare runs with and without the skill and preserve transcripts. The suite covers triggering, authority gates, repository preparation, role persistence, event recovery, Hunk identity and comment preservation, stale heads, scope and review budgets, permissions, conflicts, reviewer-only publication, post-review reentry, dashboard output, and guarded cleanup.

Every passing run must preserve one task/workspace/worktree identity, bounded roles and loops, independently validated transitions, human-owned scope and finalization, reviewer independence, no primary-branch mutation or merge, and no loss of dirty, active, unrecoverable, or ambiguous state.
