# Stagehand Design Principles

## Purpose

Stagehand helps one developer coordinate coding agents while producing pull
requests that fit ordinary human team practices. It automates workflow
coordination without taking implementation or independent-review ownership.
Ordinary tasks retain human product and merge authority. A separately chartered
autonomous project may delegate bounded specification decisions and non-main
integration-branch squash merges to the orchestrator.

This document preserves the reasoning behind the workflow. Operational details
belong in the [orchestration skill](../../skills/orchestrating-development/SKILL.md),
and its detailed design and evaluation contract lives in the
[skill specification](../../skills/.specs/orchestrating-development-spec.md).

## Origin

The workflow began as a manually coordinated author-reviewer loop. That manual
model established the durable contracts before Herdr automation was introduced:

1. A human selects one cohesive change and discusses the implementation with an
   author agent.
2. The persistent author implements and verifies the approved plan, then creates
   an intent-bearing draft pull request.
3. A separate persistent reviewer audits the complete changeset.
4. Review findings return to the original author through a private local surface,
   normally Hunk.
5. The same reviewer performs complete rereviews until the change passes or the
   workflow returns to the human.
6. The human authorizes readiness and ultimately merges through GitHub.

Stagehand coordinates these transitions through Herdr. It does not replace the
underlying contracts or turn the orchestrator into an author, reviewer, or fixer.

## Guiding Principles

- **Supervised human authority:** For ordinary tasks, the human chooses work,
  approves implementation plans, controls scope, disposes ambiguous findings,
  authorizes pull-request finalization, and performs every merge.
- **Chartered autonomy:** A human may instead authorize one durable project
  envelope containing authoritative documents, allowed repositories, exact
  integration branches, terminal evidence, deferred gates, and resource limits.
  Authority outside that envelope remains human-owned.
- **Explicit intent:** The author and human establish enough context to
  distinguish required behavior, constraints, and non-goals. The draft pull
  request becomes the durable team-facing statement of that intent.
- **Cohesive scope:** Each workspace carries one feature, bug fix, or similarly
  focused change. Review discoveries do not silently become additional work.
- **Independent review:** A reviewer separate from the author evaluates the
  complete changeset against its stated intent and surrounding repository code.
- **Persistent roles:** The same author and reviewer normally survive the entire
  review loop, retaining useful design and investigation context without making
  conversation history the source of truth.
- **Proportional rigor:** Planning, verification, and review depth follow actual
  risk and complexity. Small changes should not inherit ceremonial overhead.
- **Material feedback:** Review may investigate broadly, but it should surface
  evidence-backed findings that affect correctness, safety, compatibility,
  maintainability, or the claimed behavior.
- **Controlled repair:** The author resolves only findings selected for the
  current pull request. Tangential improvements remain outside its scope unless
  the human explicitly expands the task.
- **Traceable evolution:** Material corrections to authoritative product intent
  update the owning specification and a checked-in decision record before or
  with dependent implementation.
- **Cohesive implementation:** Components own narrowly defined responsibilities;
  cross-layer logic, duplicated contracts, speculative frameworks, and
  abstraction without a current seam are defects rather than flexibility.
- **Evidence over confidence:** Readiness depends on inspectable code, relevant
  tests or other verification, and an explicit review outcome.
- **Recoverable state:** Branches, pull requests, task records, review findings,
  and verification evidence must permit recovery when an agent session is lost.
- **Team-compatible output:** Local agent iteration culminates in a concise
  GitHub pull request for final human, teammate, CI, and policy review.
- **Replaceable tools:** Herdr and Hunk implement workflow seams; product intent
  and role contracts should not depend on one terminal, model, or company.

## Responsibility Boundaries

- **Human:** Selects ordinary work and owns its checkpoints. For an autonomous
  project, defines the charter and retains every authority it does not delegate,
  including all operations involving `main`.
- **Orchestrator:** Provisions isolated workspaces, records workflow state,
  launches and monitors roles, routes validated handoffs, applies resource and
  safety limits, and reports decisions that require the human. As Autonomous
  Project Integration Director, it may also schedule chartered packages,
  approve bounded plans without routine human checkpoints, record specification
  decisions, and squash-merge only into recorded integration branches.
- **Author:** Explores the repository, proposes the implementation plan,
  implements only after approval, verifies the result, creates the draft pull
  request, and resolves selected findings.
- **Reviewer:** Independently reviews the current complete changeset, records
  findings, rereviews author fixes, and finalizes a passing pull request only
  after human authorization.

Role continuity is an efficiency mechanism, not authority. Durable artifacts and
current changeset identity remain authoritative when a role must be replaced.

Autonomous monitoring is event-first but not event-dependent. A recorded
multi-minute watchdog batches lifecycle inspection, reads transcripts only when
settlement or contradictory evidence warrants it, and backs off during healthy
long operations. Portable loopback, user-space, or preauthorized isolated
container simulations are preferred; managed roles never elevate privileges or
mutate host networking, and privileged scenarios remain unexecuted manual
evidence until the human approves an exact procedure.

## Architectural Choices

- The orchestrator is a thin coordination layer over focused author and reviewer
  skills rather than one monolithic coding agent.
- Supervised implementation planning stays between the human and author. In an
  autonomous project, the author proposes the plan to the orchestrator, which
  retains only its bounded scope and evidence contract after approval.
- GitHub draft pull requests carry intent and recovery context; Hunk carries
  private iterative review feedback without polluting the shared review timeline.
- Semantic workflow events complement Herdr lifecycle state. Terminal activity
  alone cannot prove plan approval, implementation completion, review outcome, or
  permission to mutate shared state.
- One Herdr workspace and worktree owns one active task lineage. Supervised
  parallelism remains a human decision; autonomous parallelism follows the
  charter's dependency graph, reservations, and capacity.
- The original author fixes findings and the original reviewer rereviews them.
  Spawning a fresh fixer or reviewer each round wastes context and weakens
  accountability.
- Review and scope loops are bounded. Repeated failures, stale changeset identity,
  conflicting conclusions, or lack of progress return to the human in
  supervised mode and invoke chartered convergence recovery in autonomous mode.
- Repository-specific paths, build policy, hosts, and initialization behavior
  belong in private local configuration rather than the reusable skill.
- Autonomous project dependencies, package evidence, scope reservations, and
  integration heads belong in durable project records rather than conversation
  history or free-form wait text.
- Guarded publication binds an author to one canonical task record and exact
  feature-branch head. Guarded integration binds the named orchestrator to
  canonical charter records, current governing identities, a non-queued base,
  PR evidence, required checks, and squash strategy before external mutation.

## Boundaries and Non-Goals

Stagehand does not implement product code, independently review its own
integration decision, silently expand scope, approve unexpected risky
operations, or replace repository instructions, CI, branch protection,
required reviews, or company policy. Autonomous merge authority is limited to
the chartered non-main integration branch. No agent works on, pushes to, or
merges into `main`.

The workflow is intentionally compatible with native and container builds,
C++, worktrees, submodules, and meta-repositories, but their concrete behavior
remains repository-specific. Stagehand coordinates the documented boundary; it
does not invent build or source-management policy for a target repository.
