# Skill Composition

## Purpose

Stagehand coordinates a set of focused skills without absorbing their judgment
or procedures into one monolithic orchestrator. This document explains how those
skills work together and preserves the boundaries that keep authoring, review,
repair, and GitHub mutation accountable.

Stagehand owns the orchestration contract. SkillDex owns the author and reviewer
workflow skills. Hunk and Herdr provide integration skills for their respective
tools. Each source repository remains authoritative for the detailed behavior of
the skill it distributes.

## Composition Map

| Skill | Role | Invocation point | Consumes | Produces |
| --- | --- | --- | --- | --- |
| `orchestrating-development` | Orchestrator | Explicit request in the dedicated control workspace | Human-authorized task, local policy, task records, and managed-role events | Herdr topology, validated transitions, and human attention requests |
| `herdr` | Orchestrator | When inspecting or controlling Herdr resources | Recorded workspace, pane, worktree, or agent identity | Observable runtime state or a bounded Herdr operation |
| `writing-specifications` | Human and author | Optional architectural work before implementation | Goals, constraints, boundaries, and design questions | An agreed design artifact or implementation context |
| `preparing-pull-requests` | Author | After implementation is ready and Stagehand requests draft creation | Confirmed intent, current branch, verification evidence, and issue context | Intent-bearing draft pull request and `draft-pr-ready` handoff |
| `reviewing-code` | Reviewer | After the draft and exact changeset are validated | Pull-request context, repository guidance, base and head, and surrounding code | Material findings or a current-head review pass |
| `hunk-review` | Reviewer | During private review of a Stagehand-authored change | Verified Hunk session and current changeset | Inline private findings for the author |
| `resolving-findings` | Original author | After the human selects findings for this pull request | Selected findings, current intent, and author context | Focused fixes, verification evidence, and `fixes-ready` handoff |
| `preparing-pull-requests` | Reviewer | After a current-head pass and explicit human authorization | Reviewed head, final evidence, limitations, and existing PR description | Reconciled description, ready-for-review state, and `pull-request-finalized` handoff |

## End-to-End Handoffs

1. **Select and provision.** The human authorizes a task. Stagehand records its
   boundaries and uses the Herdr skill to create one isolated workspace and
   worktree.
2. **Plan with the author.** The author explores and proposes a plan. The human
   approves implementation directly with that author. Architectural work may use
   `writing-specifications`, but ordinary changes do not require a permanent spec.
3. **Implement and draft.** The author implements and verifies the approved
   change. Stagehand then asks that same author to use
   `preparing-pull-requests` to create the draft and durable intent handoff.
4. **Review independently.** Stagehand starts a separate reviewer against the
   exact draft head. The reviewer combines `reviewing-code` judgment with
   `hunk-review` as the private feedback surface.
5. **Dispose and resolve.** The human selects which findings belong in the
   current pull request. The original author uses `resolving-findings` only for
   that selected set.
6. **Rereview completely.** The same reviewer reviews the complete updated
   changeset. Stagehand repeats the bounded review-and-fix loop without replacing
   roles or automatically expanding scope.
7. **Finalize deliberately.** After a passing review, the human may authorize the
   reviewer to use `preparing-pull-requests` in finalization mode. GitHub team
   review and merge remain outside the managed loop.

For reviewer-only work on another developer's pull request, Stagehand invokes
`reviewing-code` without an author, fixer, or Hunk requirement. The reviewer
creates a proposal for the exact head and publishes it only after the human
approves that proposal.

## Skill Ethos and Boundaries

### `orchestrating-development`

The orchestrator coordinates state and authority; it does not implement, review,
fix, or merge product code. It treats Herdr lifecycle as observation rather than
proof, validates semantic handoffs against durable artifacts, warns about task
overlap, and stops at human decisions or bounded workflow limits.

### `writing-specifications`

Specification work clarifies architecture, intent, boundaries, and interfaces
before implementation. It is proportional and optional: a small change may need
only a conversational plan, while a consequential design may need a durable
document. The skill does not authorize implementation or replace repository
requirements.

### `preparing-pull-requests`

Pull-request preparation preserves confirmed intent while presenting the actual
implementation and verification evidence accurately. Draft creation belongs to
the author; finalization belongs to the reviewer after a passing current-head
review and human authorization. The skill does not perform review, approve its
own claims, merge, or silently redefine scope.

### `reviewing-code`

Review is independent, complete, and proportional to risk. The reviewer acquires
intent from the pull request, linked requirements, discussion, and repository
context, then inspects both the changes and surrounding code. It investigates
broadly but surfaces only material, evidence-backed findings. It does not fix the
code, inflate the pull request with tangential work, or treat a prior pass as
valid after the head changes.

### `hunk-review`

Hunk is a private transport and note-taking surface, not the source of intent or
review judgment. Stagehand uses one non-watching session for the task. Existing
comments remain available until the author consumes them; reload occurs only
before rereview because it may clear or invalidate comments.

### `resolving-findings`

Finding resolution returns implementation to the original author, preserving its
design and repository context. It modifies only the human-selected, current-scope
set, performs proportionate verification, and hands the complete changeset back
to the same reviewer. Valid tangential observations remain follow-up candidates
unless the human explicitly expands scope.

## Shared Authority Boundaries

- A skill invocation supplies procedure, not missing human authority.
- The draft pull request is the durable statement of intent; Hunk carries private
  findings; the task record carries orchestration state.
- Every changed head requires complete independent review before finalization.
- Neither a favorable review nor green CI authorizes readiness, publication, or
  merge by itself.
- Stagehand may route work between skills, but it never automatically begins a
  new task or converts a reviewer observation into authorized scope.
- The human performs the final GitHub review and merge.
