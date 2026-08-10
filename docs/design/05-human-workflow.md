# Human Workflow

## Playbook Overview

The developer operates the workflow through short, explicit requests to a persistent author agent and a separate persistent reviewer agent. Ordinary implementation remains conversational. Skills activate only at recognizable transitions such as creating a draft pull request, starting a formal review, resolving selected findings, or finalizing a reviewed pull request.

Natural language is the portable interface. Slash commands and Herdr prompt aliases may shorten common requests, but the workflow must remain usable without them.

## Establishing Roles

The agent that develops the change naturally becomes the **author** through its existing conversation and repository context. It does not need a persona prompt or an authoring skill.

The developer establishes the **reviewer** once with an explicit formal-review request directed to a separate agent session. The reviewer remains separate from implementation and normally retains its session through every rereview. A role is session context plus current artifacts, not a permanent identity stored by the workflow.

If a session is replaced, the developer explicitly assigns the replacement role and supplies the current pull request or selected-finding handoff. Recovery follows the durable sources in [`10-change-context.md`](./10-change-context.md).

## Expected Transitions

| Developer request | Session | Expected skill behavior |
| --- | --- | --- |
| “Implement this feature” | Author | Normal coding behavior; no workflow skill |
| “Create a draft pull request” | Author | Load [`preparing-pull-requests`](./55-preparing-pull-requests.md) in draft mode |
| “Review PR #123” | Reviewer | Load [`reviewing-code`](./30-reviewing-code.md) |
| “Review PR #123 in Hunk” | Reviewer | Load reviewing-code plus the existing Hunk review skill |
| “Summarize these comments” | Either | Discuss only; do not activate finding resolution |
| “Address selected findings F1 and F3” | Author | Load [`resolving-findings`](./40-resolving-findings.md) |
| “Rereview PR #123 after the fixes” | Reviewer | Load reviewing-code and refresh the complete changeset |
| “Finalize this reviewed PR and mark it ready” | Reviewer | Load preparing-pull-requests in finalization mode |
| “Merge this pull request” | Either | Decline agent execution; the developer merges in GitHub |

Equivalent natural wording should work. The important signal is explicit user intent to cross a workflow boundary, not an exact phrase.

## Automatic Skill Routing

Agents initially see skill names and trigger descriptions, then load full instructions when a request matches. Automatic use therefore depends on precise metadata and is routing, not background automation.

Trigger descriptions should cover likely natural wording while excluding near misses:

- mentioning a pull request does not itself authorize creating or updating one;
- inspecting code does not itself request formal review;
- discussing feedback does not authorize code modification; and
- a readiness recommendation does not authorize changing GitHub state.

The skill packages must be evaluated with both expected prompts and similar prompts that must not trigger. When routing is uncertain or the action affects shared state, the developer may name the skill explicitly.

## Optional Shortcuts

An agent interface or Herdr configuration may offer aliases such as `/draft-pr`, `/review-pr`, `/resolve-review`, `/rereview-pr`, and `/finalize-pr`. Each alias should expand to an ordinary request that identifies the target and applicable skill.

Aliases are convenience and determinism layers only. They must not conceal authorization, automatically advance to another stage, or make the workflow dependent on Herdr. The core skills remain independently usable by another compatible agent interface.

## Handoff Visibility

Agents do not exchange hidden state. Each producing skill coaches the next handoff through an explicit artifact:

- the author creates a structured draft pull request for the reviewer;
- the reviewer places normalized findings in Hunk or an authorized GitHub review;
- the developer selects findings for the current pull request;
- the author reports resolution status and verification evidence;
- the reviewer produces a readiness recommendation; and
- after authorization, the reviewer finalizes the pull-request description and state.

The developer remains the controller between transitions. No skill starts another agent, automatically chains into another pull request, or infers authorization from the previous agent's output.

## Session Continuity and Recovery

Persistent sessions reduce repeated repository discovery and preserve design or review history. They are an optimization, not the source of truth. The branch, pull request, Hunk findings or recovery snapshot, verification evidence, and developer-confirmed intent must remain sufficient to replace either agent.

The same reviewer performs a complete current base-to-head review after every fix round. Retained context helps it revisit prior concerns but does not permit a delta-only rereview.

## Human Control Boundary

The developer explicitly controls scope changes, finding disposition, shared publication, ready-for-review authorization, and merge. Skills may proceed autonomously inside an already approved boundary, but an agent must not treat role continuity, a slash command, or an earlier approval as authorization for a later external action.
