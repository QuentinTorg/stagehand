# Skill Composition

Stagehand coordinates; [Skilldex](https://github.com/QuentinTorg/skilldex) supplies the author/reviewer methods. Herdr manages runtime resources. Workers do not load Stagehand or produce its bookkeeping.

| Component | Consumer | Responsibility |
| --- | --- | --- |
| `orchestrating-development` | Coordinator | Task ownership, workspace setup, handoffs, progress, human decisions, and recoverable state |
| Herdr skill | Coordinator | Installed CLI and runtime semantics |
| Agent Wake Relay | Herdr runtime | Persistent identity-bound watches and durable, bounded wake delivery |
| Status board | Human | Saved progress, live activity, task navigation, and messages to the coordinator |
| `preparing-pull-requests` | Author, then authorized reviewer | Intent-bearing draft, then evidence-based finalization |
| `reviewing-code` | Independent reviewer | Complete phased review grounded in intent and surrounding code |
| `resolving-findings` | Original author | Selected in-scope repairs and proportionate verification |
| `writing-specifications` | Human/author, optionally | Architectural intent when a conversational plan is insufficient |

## Workflow and ethos

This is the default human-directed workflow. [Explicit project delegation](../../skills/orchestrating-development/references/project-delegation.md) lets the same coordinator exercise named decisions for an agreed outcome; it adds no role or default authority.

The human selects work and discusses implementation with the author. After approval, the author implements, verifies, and prepares the draft in one assignment. The draft preserves human intent separately from delivered behavior, tests, limitations, and non-goals; supplied issues are linked without claiming unfulfilled scope is resolved.

A separate reviewer uses GitHub description, discussion, previous comments, linked requirements, and surrounding code. It investigates broadly but surfaces material, evidence-backed findings, not a quota of comments. The original author resolves only selected findings; tangential ideas remain follow-ups. The same reviewer assesses the complete updated changeset.

After a current-head pass, the human authorizes the reviewer to finalize. Finalization improves factual impact, risk, verification, and navigation context without rewriting intent. Human teammates review and merge through GitHub. Neither a favorable review nor green CI grants merge authority.

Skilldex owns these review and preparation methods. Stagehand's short assignment reminders preserve the important handoff context without copying skill internals. Skills remain medium-agnostic; ordinary responses carry private findings, and Hunk is not required.

## Observation, not worker protocol

The coordinator registers watches, reads normal worker answers when woken, verifies consequential evidence, and saves meaningful outcomes. Workers need no endpoint, JSON, phase notification, or scope-update handshake. Direct human instructions remain effective without a second approval in another pane.

The relay knows runtime identity and settlement, not intent or success. The board renders progress but does not decide it. State records support recovery without becoming an event diary. See [State and Wakeups](../../skills/orchestrating-development/references/workflow-state.md).

## Other work

Reviewer-only assignments propose an external GitHub review without modifying source or PR state, then publish only after human approval of that proposal and head.

Delegated investigation, diagnosis, planning, and research use one bounded worker and no implied PR loop. Workspace-only tasks provide an open-ended working area. A human request to implement or review a resulting fix can promote the same workspace and agent into development; it need not start a duplicate task.

Operational authority, model selection, and cleanup details belong in the [orchestration skill](../../skills/orchestrating-development/SKILL.md), not in every worker prompt.
