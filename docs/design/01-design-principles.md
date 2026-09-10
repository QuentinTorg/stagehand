# Stagehand Design Principles

## Purpose

Stagehand helps one developer coordinate coding agents while producing pull
requests that fit ordinary human team practices. It automates workflow
coordination without taking authorship or independent-review authority. Human-led
work remains the default; a bounded local builder charter may delegate routine
delivery judgment and non-main squash integration to the orchestrator.

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

- **Explicit authority:** The human owns every checkpoint by default. A local
  builder charter may delegate project delivery checkpoints and exact non-main
  squash integration while retaining named high-risk decisions for the human.
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
- **Evidence over confidence:** Readiness depends on inspectable code, relevant
  tests or other verification, and an explicit review outcome.
- **Recoverable state:** Branches, pull requests, task records, review findings,
  and verification evidence must permit recovery when an agent session is lost.
- **Team-compatible output:** Local agent iteration culminates in a concise
  GitHub pull request for final human, teammate, CI, and policy review.
- **Replaceable tools:** Herdr and Hunk implement workflow seams; product intent
  and role contracts should not depend on one terminal, model, or company.

## Responsibility Boundaries

- **Human:** Defines authority and owns intent, high-risk decisions, and final
  integration by default.
- **Orchestrator:** Provisions isolated workspaces, records workflow state,
  launches and monitors roles, routes validated handoffs, applies resource and
  safety limits, and reports decisions that require the human. Under a builder
  charter it also owns the delegated delivery decisions and non-main squash merge.
- **Author:** Explores the repository, proposes the implementation plan,
  implements only after approval, verifies the result, creates the draft pull
  request, and resolves selected findings.
- **Reviewer:** Independently reviews the current complete changeset, records
  findings, rereviews author fixes, and finalizes a passing pull request only
  after human authorization.

Role continuity is an efficiency mechanism, not authority. Durable artifacts and
current changeset identity remain authoritative when a role must be replaced.

## Architectural Choices

- The orchestrator is a thin coordination layer over focused author and reviewer
  skills rather than one monolithic coding agent.
- Detailed implementation planning stays between the human and author so the
  orchestrator can retain a smaller, task-level context.
- GitHub draft pull requests carry intent and recovery context; Hunk carries
  private iterative review feedback without polluting the shared review timeline.
- Semantic workflow events complement Herdr lifecycle state. Terminal activity
  alone cannot prove plan approval, implementation completion, review outcome, or
  permission to mutate shared state.
- One Herdr workspace and worktree owns one task. Parallel task count remains a
  human decision, with the orchestrator warning about likely overlap.
- The original author fixes findings and the original reviewer rereviews them.
  Spawning a fresh fixer or reviewer each round wastes context and weakens
  accountability.
- Review and scope loops are bounded. Repeated failures, stale changeset identity,
  conflicting conclusions, or lack of progress return to the human.
- Repository-specific paths, build policy, hosts, and initialization behavior
  belong in private local configuration rather than the reusable skill.

## Boundaries and Non-Goals

Stagehand does not implement product code, silently expand scope, approve
unexpected risky operations, or publish an external review without permission.
Outside a builder charter it does not select or merge work; inside one it remains
bounded to named repositories and non-main integration branches. It does not
replace repository instructions, CI, branch protection, required reviews, or
company policy.

The workflow is intentionally compatible with native and container builds,
C++, worktrees, submodules, and meta-repositories, but their concrete behavior
remains repository-specific. Stagehand coordinates the documented boundary; it
does not invent build or source-management policy for a target repository.
