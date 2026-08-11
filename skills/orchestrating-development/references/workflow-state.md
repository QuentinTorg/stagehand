# Workflow State and Events

## Sections

- [State ownership](#state-ownership)
- [Task states](#task-states)
- [Semantic events](#semantic-events)
- [Missing-event reconciliation](#missing-event-reconciliation)
- [Event validation](#event-validation)
- [Review counters and scope versions](#review-counters-and-scope-versions)
- [Recovery](#recovery)
- [Cleanup](#cleanup)

## State ownership

Herdr reports terminal and agent lifecycle. The task record reports workflow state. Keep them separate: an `idle` author may be awaiting plan approval, while a `done` reviewer may have findings rather than approval.

The orchestrator owns one task record per authorized task. A task owns exactly one feature worktree and one managed Herdr workspace for its entire lifetime. A development task uses the fixed tab-and-pane topology in [Hunk Coordination](hunk-coordination.md): author and reviewer share the `agents` tab side-by-side, while Hunk occupies its own unsplit `hunk` tab. A reviewer-only task has only its reviewer pane.

Every state transition updates `state.waiting_on`, `state.attention_required`, and `state.attention_reason` together with the state name. `waiting_on` identifies the next actor, event, decision, check, dependency, or cleanup condition in plain language for controller recovery; it is not a dashboard field. Attention is true only when a concrete human action is currently required; ordinary agent work, CI, or an expected semantic event is a wait condition but not human attention.

When a managed role owns the next transition, also record `event_recovery.expected_role`, the allowed `expected_events`, and zero recovery attempts. Clear that expectation when a valid event or human decision transfers ownership elsewhere. For legacy records, derive and persist these fields from the validated state before attempting recovery.

## Task states

| State | Meaning | Normal exit |
| --- | --- | --- |
| `queued` | Authorized but intentionally waiting for a human decision, dependency, requested sequencing, or conflict resolution | Start the task when its waiting condition is cleared |
| `planning` | Author is exploring and discussing implementation with the human | Validated `implementation-started` or `needs-human` event |
| `implementing` | Author is implementing or verifying the approved scope | Validated `implementation-ready` or `needs-human` event |
| `drafting` | Orchestrator directed the author to create the initial draft PR | Validated `draft-pr-ready` or `needs-human` event |
| `reviewing` | Reviewer is performing a complete review of the current changeset | Validated reviewer outcome |
| `review-awaiting-publication` | Reviewer-only proposal is validated for the current head | Human disposition of the exact proposal |
| `publishing-review` | Human authorized reviewer-only publication for the exact proposal and head | Validated `review-published` or `review-needs-human` event |
| `review-complete` | Authorized reviewer-only review was published | Human-directed retention or cleanup |
| `resolving` | Original author is resolving the selected current-change findings | Validated `fixes-ready` or `needs-human` event |
| `decision-required` | Progress requires human scope, risk, permission, conflict, or budget judgment | Explicit human disposition |
| `ready-candidate` | Reviewer passed the exact current head | Human finalization decision or selected post-review feedback |
| `finalizing` | Human authorized the reviewer to finalize the exact reviewed head | Validated `pull-request-finalized`, `review-needs-human`, or selected post-review feedback that invalidates it |
| `ready-for-team-review` | Reviewer finalized the passing current head and orchestration validation succeeded | External human review, selected post-review feedback, or merge decision |
| `merged` | GitHub confirms the pull request merged | Guarded cleanup |
| `closed` | Human closed, superseded, or otherwise ended the task | Explicit cleanup or archival decision |
| `cleaned` | Task-owned Herdr workspace and worktree were safely removed | None |

Waiting for the human does not imply failure. Record the prior state and reason before entering `decision-required` so an authorized decision can resume the correct transition.

## Semantic events

Managed agents send compact JSON as a prompt to the stable `workflow_orchestrator` agent without `--wait`. The common envelope is:

```json
{
  "kind": "workflow-event",
  "task": "reconnect-race",
  "role": "author",
  "event": "draft-pr-ready",
  "scopeVersion": 1,
  "head": "0123456789abcdef"
}
```

Required events are:

| Role | Event | Additional fields | Meaning |
| --- | --- | --- | --- |
| Author | `implementation-started` | none | Human explicitly approved implementation in the author session |
| Author | `implementation-ready` | `head`, `verificationRef` | Approved implementation is ready for the orchestrator to request draft creation |
| Author | `draft-pr-ready` | `base`, `head`, `pullRequest` | Initial draft contains intent and the verified current head |
| Author | `fixes-ready` | `base`, `head`, `pullRequest` | Selected findings were processed and the new head is ready |
| Author | `scope-revised` | `briefRef`, optional `summary` | Human explicitly revised material scope |
| Author | `post-review-changes-started` | `head`, `feedbackRef`, `changeClass`, optional `briefRef` | Human selected changes after successful review; class is `small-fix` or `material` |
| Author | `needs-human` | `reason` | Author cannot proceed inside existing authority |
| Reviewer | `review-findings` | `base`, `head`, `round`, `findingCount`, `hunkSession` | Material current-change findings were recorded |
| Reviewer | `review-passed` | `base`, `head`, `round`, `pullRequest` | Complete review found no known material in-scope defect |
| Reviewer | `pull-request-finalized` | `base`, `head`, `round`, `pullRequest` | Human-authorized reviewer finalization completed for that exact head |
| Reviewer | `pull-request-returned-to-draft` | `base`, `head`, `pullRequest` | Authorized post-readiness draft transition completed without other PR mutation |
| Reviewer | `review-needs-human` | `base`, `head`, `round`, `reason` | Review requires a human decision |
| Reviewer | `review-proposed` | `base`, `head`, `round`, `conclusion`, `proposalRef` | Reviewer-only output is ready for human inspection and is not published |
| Reviewer | `review-published` | `base`, `head`, `round`, `pullRequest`, optional `reviewUrl` | Human-authorized reviewer-only output was published for the exact head |

Free-form summaries are supporting context, not transition authority. A managed role verifies delivery from a successful command result reporting `type: agent_prompted`. If direct delivery fails twice, the agent prints `WORKFLOW_EVENT_FALLBACK` and the complete event in its final response. The orchestrator may recover it with `herdr agent read`, validate it, and record that fallback source.

Authors use `needs-human` and reviewers use `review-needs-human` for any diagnosed blocker that prevents their expected success event. These blocker events are valid from every active state owned by that role. Initialization, verification, Hunk, GitHub, publication, and finalization failures do not create new event names.

### Shared-input collision recovery

Herdr event delivery and human typing use the same interactive orchestrator input. An event prompt can arrive while the human has an unsent draft, append its JSON to that draft, and submit both as one user message. This transport race does not make either part invalid.

When a message contains human text followed by one or more complete JSON objects whose `kind` is `workflow-event`:

1. separate the human prefix from each complete trailing event;
2. preserve and respond to the human instruction as human input rather than treating it as event metadata;
3. validate every event independently through the normal event-validation procedure; and
4. give the human instruction authority when it conflicts with a concurrently delivered event, rejecting or reconciling the event as stale where appropriate.

Do not discard the human prefix, treat the JSON as part of the human command, or accept the combined blob as one semantic instruction. If the boundary is ambiguous, an event is incomplete or interleaved, or the human intent cannot be recovered confidently, preserve the raw input, make no transition from the uncertain event, inspect the named managed agent and durable state, and ask the human only for the portion that remains unclear.

## Missing-event reconciliation

The orchestrator is not a background daemon. It performs this bounded check whenever it is invoked to monitor or report and whenever a task is otherwise being reconciled. A silent delivery failure cannot wake the orchestrator by itself; hooks or an external controller would be required for immediate unattended detection.

Reconciliation determines the **furthest proven state**, not merely the next missing event. Keep four evidence classes separate:

- explicit human authority comes from the current instruction or an unambiguous human message visible in the managed-agent transcript;
- role claims come from valid events, verified delivery output, transcript fallbacks, or a catch-up event requested during reconciliation;
- Git, GitHub, verification artifacts, and Hunk prove observable work and changeset identity but never prove human authority or a review conclusion by themselves; and
- Herdr lifecycle proves only runtime activity or settlement.

For each task whose record, managed role, or durable artifacts may disagree:

1. Start with one bounded Herdr inventory and the task record. If lifecycle and recorded state agree and no drift signal exists, do not load transcripts or query every external artifact.
2. When the role settles unexpectedly, an expected event is absent, or branch/PR/Hunk evidence is ahead of the record, inspect that role's recent transcript once and only the durable artifacts needed to identify a candidate state. Recover and validate any complete event or fallback first. A live permission request follows the permission procedure instead of receiving a queued recovery prompt.
3. Identify every workflow boundary between the recorded state and candidate furthest state. Prove each human-authority gate from actual human input, each role-owned conclusion from role output or an event, and each changeset transition from durable artifacts. An agent's paraphrase that the human approved something is not authority.
4. If every intervening boundary is proven, advance the record directly and atomically to the furthest proven state. Do not ask the agent to replay obsolete `implementation-started`, `implementation-ready`, or other historical handoffs. Record the reconciliation sources and skipped boundaries in `state.decision_reason`, normalize `last_event` when a recovered current-boundary event exists, and reset the expected role, events, wait condition, attention fields, and recovery attempts for the resulting state.
5. If human authority and observable work are proven but the current role-owned conclusion is missing, record one recovery attempt and prompt that same role once with a rendered control block. Give the exact schema for the single existing event that describes its current boundary, even when accepting it will atomically catch the record up across older proven boundaries. Ask it to report current state, not redo work or emit a chain of historical events.
6. If the role is still working and only bookkeeping lag is proven, update the record to the proven active state without interrupting authorized work, then wait for its normal next boundary. If the observed mutation lacks authority or continuing could compound risk, use the configured interrupt boundary and return to the human.
7. If any skipped authority, role conclusion, task identity, scope version, or changeset identity remains ambiguous—or the one catch-up attempt settles without a valid result—enter `decision-required`, preserve all work, and ask one focused human question. Never infer the missing fact, repeatedly pump the role, spawn a replacement, or increment review counters.

Reset `event_recovery.attempts` only after successful atomic reconciliation or when a valid event establishes a new expected handoff. A malformed, stale, wrong-role, or wrong-scope event does not reset it. If the task record and transcript disagree about human authority, preserve state and ask the human rather than choosing the more advanced account.

## Event validation

Before advancing state:

1. Confirm the task exists and the emitting role matches the task's named live agent.
2. Confirm the event is valid from the current task state. During an active catch-up, it may instead match the candidate current boundary only when every skipped transition was independently proven by the reconciliation procedure.
3. Confirm `scopeVersion` matches the task record.
4. Resolve the worktree, branch, base, pull request, and current head independently.
5. Reject stale or contradictory events and move to `decision-required` when reconciliation could change behavior.

An event is a claim, not proof. Validate the draft PR and head before development review, validate `review-passed.head` before asking for finalization authority, and validate that `pull-request-finalized.head` still equals the ready pull request's head before declaring development orchestration complete. For reviewer-only work, validate the proposal artifact, conclusion, and current head before requesting publication authority, then validate the published review before entering `review-complete`.

Accept `post-review-changes-started` only after a successful review or finalization and only for feedback explicitly selected by the human. Preserve the former reviewed and finalized heads as history, clear both as current authority, and bind the feedback reference before resolution. Reject a concurrently arriving finalization event as stale. A material event increments the scope version using its brief reference. If draft return is required, validate `pull-request-returned-to-draft` before author implementation proceeds. A small fix does not reset review counters; material scope revision resets only the per-scope count.

## Review counters and scope versions

Increment `review.rounds_this_scope` and `review.rounds_total` when a reviewer outcome for a valid complete review is accepted. Check both budgets before beginning another review.

A human-authorized material scope revision:

1. increments `scope.version`;
2. records the new brief reference and concise intent change;
3. resets `review.rounds_this_scope` to zero;
4. preserves `review.rounds_total` and `scope.revision_count`; and
5. instructs the same reviewer to begin again with a full phase-zero review.

Fixes that merely resolve selected findings do not create a new scope version.

## Recovery

On orchestration restart, treat every cached lifecycle observation as stale. Reconcile, in order:

1. task record and configured repository identity;
2. worktree path, branch, base, status, and current head;
3. draft pull request, description, state, and remote head;
4. live Herdr workspace, panes, and named agents; and
5. Hunk session source when a development task is in review, or the proposal artifact for reviewer-only work.

Resume only after these sources agree. Never repeat workspace creation, PR creation, comment publication, or finalization merely because the previous command result was lost.

## Cleanup

A task becomes cleanup-eligible when GitHub confirms its pull request merged or the human explicitly requests cleanup. Before removal, verify that the worktree and workspace still belong to the task, no managed role is working, and apply the two-layer recoverability audit in [Safety, Capacity, and Escalation](safety-and-escalation.md). An expected containing-repository gitlink difference is allowed only for a clean, recoverable submodule target whose recorded pointer update is `not-planned`; it does not excuse changes inside that submodule.

If any safety check fails, enter `decision-required` and preserve the workspace. Otherwise remove only the task-owned Herdr workspace and worktree through the normal path or the audited submodule-specific force exception, mark the record `cleaned`, and retain or archive the task record. Pull-request closure and branch deletion are separate actions and are not implied by workspace cleanup.
