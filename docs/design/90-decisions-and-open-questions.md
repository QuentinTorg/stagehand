# Decisions and Open Questions

## Purpose

This document preserves design history, implementation questions, and deferred choices. It is non-normative: when it conflicts with another design document, the numbered workflow contract that owns the subject is authoritative.

## Confirmed Decisions

- The workflow serves an individual developer while producing ordinary team-compatible GitHub pull requests.
- One cohesive feature, bug fix, or equivalent change moves through the workflow at a time.
- A persistent author agent and separate persistent reviewer agent form the normal private loop.
- The implementation conversation establishes the author role; the developer assigns the reviewer role once in a separate session.
- The original author resolves selected findings; a third implementation agent is not required.
- The same reviewer normally performs every rereview, always against the complete current changeset.
- Agent continuity improves efficiency but does not replace durable change context and handoff artifacts.
- The developer owns intent, scope, finding disposition, external publication, readiness authorization, and merge.
- The reviewer may finalize and mark a pull request ready only after a successful final review and explicit developer authorization.
- GitHub draft pull requests are the durable team boundary; Hunk is the default private review surface.
- Local review churn is not copied into the GitHub timeline for the developer's own pull request.
- Reviews are medium-independent; Hunk and GitHub are transport adapters.
- Review uses adaptive independent phases without mandatory user pauses between phases.
- Phase 0 is a high-level architectural pass; later independent passes exist to catch material issues it misses.
- Review investigation remains broad while surfaced feedback is filtered to material, evidence-backed findings.
- Every behavior-changing change receives a focused correctness pass even when other review concerns are inapplicable.
- Reviewer communication uses concise professional disposition rather than a prescribed persona or praise style.
- Review size affects strategy but has no fixed rejection threshold.
- Tangential findings do not enter the current pull request without developer disposition.
- The initial implementation has three custom skills: preparing pull requests, reviewing code, and resolving selected findings.
- Authoring and human control are workflow contracts rather than skills; the preparation skill implements only authorized pull-request transitions.
- Short, explicit natural-language requests are the portable trigger contract.
- Automatic skill use is routing at user-requested transitions, not background workflow execution.
- Slash commands and Herdr prompt aliases are optional convenience layers rather than requirements.
- GitHub CI, branch protections, required reviews, and company policy remain external enforcement.
- Every merge is performed by the developer through GitHub; squash merge is the expected strategy.
- Multi-agent orchestration, worktree allocation, and parallel scheduling remain outside the core workflow.

## Superseded Ideas

The following historical ideas informed the design but are no longer current requirements:

- spawning a fresh author, reviewer, or fixer for every iteration;
- a separate finalizer role;
- mandatory user approval after every review phase;
- a fixed nineteen-check audit for every changeset;
- rejecting or pausing every review above a four-hundred-line threshold;
- requiring a repository review-notes file for every review;
- using GitHub review comments as private agent scratch space;
- automatically creating issues for every deferred observation;
- coupling review analysis directly to GitHub commands;
- assuming an uninstalled template would reliably control ordinary “create a PR” requests;
- allowing the workflow or an agent to merge; and
- packaging the entire lifecycle as one monolithic skill or controller.

## Open Skill-Design Questions

- What exact trigger descriptions reliably activate pull-request preparation, formal review, and finding resolution without capturing nearby discussion-only requests?
- Which should-trigger and near-miss prompt sets best evaluate all three skill descriptions?
- Should optional slash commands live in Herdr, individual agent interfaces, or a portable prompt-alias layer?
- Which phase prompts belong in the review skill's core instructions, and which should load through shallow references?
- How should the reviewing-code skill compose with Hunk's existing review skill: automatic adapter activation, an explicit second invocation, or another thin handoff?
- What compact classification vocabulary best balances severity, current-change relevance, and resolution risk?
- What standing authorization, if any, should allow routine selected fixes without another human checkpoint?
- Which baseline conversations and changesets should become evaluations before the existing Skilldex skills are revised and the preparation skill is added?
- Should the current feedback skill be retired immediately, retained under a narrower trigger during migration, or replaced atomically after evaluations pass?

Skill package specifications and evaluations should be created through the building-skills process before modifying the existing Skilldex implementation.

## Open Artifact and Recovery Questions

- Where should a pre-pull-request change brief live when it must survive agent-session loss but should not be committed?
- What is the smallest useful brief template for comment-only and similarly trivial changes?
- Should selected Hunk findings be exported automatically to a temporary sidecar, or only when a session is at risk?
- How should a saved review snapshot identify working-tree changes that do not yet have a commit hash?
- When the pull-request description changes during review, which changes require explicit reconfirmation of intent?
- What evidence is sufficient to resume when the author or reviewer session is replaced mid-loop?

## Open Review-Loop Questions

- When should repeated author-reviewer disagreement be escalated to the developer rather than iterated again?
- Should the workflow recommend a loop limit, a time or cost budget, or only risk-based escalation?
- Which substantive post-readiness changes should automatically return the pull request to draft?
- How should reviewer replacement work after major scope changes without losing useful prior findings?
- What proportional default pull-request template provides strong reviewer context without becoming burdensome for small changes or conflicting with repository templates?

## C++, Docker, Worktree, and Multi-Repository Questions

- Which build outputs and caches are safe to share across worktrees, and which must remain checkout-specific?
- How should expensive C++ builds progress from focused validation to broader pre-review or pre-readiness checks?
- When should Docker provide reproducibility, and when does it add unnecessary startup and storage cost?
- How should submodule changes bind parent and child pull requests to exact reviewed revisions?
- What ordering and readiness rules apply when a meta-repository coordinates several dependent pull requests?
- How should the workflow represent a changeset spanning repositories without pretending GitHub can merge it atomically?

Repository-specific answers belong in repository instructions or project documentation rather than the generic skills.

## Tooling Direction

- **Hunk:** Adopt as the initial private review and feedback surface. Validate live-session comments, selected-finding handoff, refresh behavior, and recovery snapshots during implementation.
- **Herdr:** Use as the human-operated interface for persistent author and reviewer sessions, workspaces, and worktrees. Any automatic handoff remains a future outer layer.
- **Skilldex:** Remains the home of the pull-request preparation, review, and narrow finding-resolution skills after their package specifications and evaluations are approved.
- **No Mistakes:** Retain as design inspiration for risk classification, review/fix discipline, verification, and pull-request context. Do not adopt its unbounded controller as a core dependency.

## Suggested Implementation Order

1. Define the concise change-brief and proportional pull-request-description templates.
2. Create trigger and behavior evaluations from real failures and representative small, medium, and large changesets.
3. Specify the preparing-pull-requests skill using [`55-preparing-pull-requests.md`](./55-preparing-pull-requests.md).
4. Specify and revise the reviewing-code skill using [`30-reviewing-code.md`](./30-reviewing-code.md).
5. Specify the finding-resolution skill and migration from the existing feedback skill using [`40-resolving-findings.md`](./40-resolving-findings.md).
6. Validate natural-language transitions and Hunk handoffs between a persistent author and reviewer using [`05-human-workflow.md`](./05-human-workflow.md) and [`60-review-adapters.md`](./60-review-adapters.md).
7. Exercise the complete manual workflow before considering slash-command aliases, Herdr automation, or a thinner external controller.
