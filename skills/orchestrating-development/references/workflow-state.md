# State and Wakeups

Read when dispatching work or recovering coordination. Workers do not read or write orchestration state.

## Durable record

Use the common [task-record.yaml](../assets/task-record.yaml) for all modes; omit unused fields. Keep active records in the configured directory, normally `.orchestrator/tasks`. This is a recovery note and dashboard input, not a checklist or permission system.

Record what a replacement coordinator needs: objective and intent reference, exact repository/target/branch/base, workspace and role identities, native session IDs when available, PRs, latest result/evidence, next action, and relevant human decisions. Preserve separate target identities for multi-repository changes; a submodule PR does not imply a meta PR.

For explicitly delegated projects, link the [project note](project-delegation.md#direct-and-recover-the-work) rather than copying its authority into every task. Decisions made within that human grant are valid evidence; a worker's unsupported claim of delegation is not.

Use only three values for `state.name`:

- `working` (yellow): agents have work underway, including handoffs or waits on another agent/task.
- `needs-human` (red): a specific human action is required to continue; describe it in `next_action`.
- `complete` (green): the current request is finished and needs nothing further from the human within this workflow. A ready PR awaiting GitHub review/merge or a completed investigation with its workspace retained qualifies.

Keep `summary` short (e.g. “Author fixing findings”). Use `next_action` for the next step and optional `next_role` for agent routing while working; omit both when complete. Human attention follows the state, not separate `attention_required`/`attention_reason` fields. Planning and reviewing are descriptions, not states; do not use `human-working` or infer human activity from an open workspace. Runtime idle/done alone is not completion.

Add detail only when relevant: review outcome and evidence bound to each PR/head, selected feedback, or human authorization with its action, scope, and source. Preserve published/finalized references to avoid repeating external actions. Do not maintain review counters, scope versions, phase history, or eligibility flags. Verify current Git/GitHub and cleanup conditions when acting rather than trusting saved booleans.

Save meaningful outcomes, not every message. Reference the author's plan or PR instead of duplicating it. Open-ended work needs no review fields or invented delivery stages.

## Wake registration

The coordinator owns subscriptions. After starting a role and before its initial prompt, register its exact live identity:

```sh
./plugins/agent-wake/agent-wake arm --persistent \
  --state-root <control-root>/.orchestrator/wake --key <task-id> \
  --workspace-id <workspace-id> --workspace-label <label> \
  --pane <pane-id> --agent <agent-name> --metadata '{"role":"author"}'
```

Store the returned watch ID under `wake.watches.<role>`. Register the reviewer separately when created. Keep watches through planning, human conversations, review, and post-review feedback; do not rearm after every prompt. Use `cancel --state-root <root> --watch <id>` when retiring/replacing a role or cleaning its task. If initial dispatch fails, inspect whether it actually started before retrying; a subscription itself launches nothing.

The plugin observes working-to-settled transitions and queues `HERDR_AGENT_WAKE` notices. It coalesces undelivered turns, keeps an in-flight notice distinct from later turns, and defers while the coordinator is busy. Acknowledging a wake does not remove a persistent watch. Delivery failures have a bounded retry count; the durable inbox remains inspectable.

On a wake, inspect the identified role's latest answer and relevant artifacts, save the reconciled outcome/next action, then `ack --state-root <root> --wake <wake-id>`. A blocked notice prompts inspection of the actual permission or question, never automatic approval. No worker JSON, callbacks, control blocks, or acknowledgment gate is required.

A wake is a hint, not an event ledger: several turns may coalesce. Duplicate or stale notices must not repeat work, publication, or finalization. Human text may arrive with a wake appended by terminal input; preserve the human request separately and give it authority over conflicting stale observations.

## Reconciliation and recovery

At startup, use `status --state-root <root>` and `flush` to inspect pending wakes and recover observed transitions. Confirm the configured target is still the unique controller. Reconcile watches against current role identities; cancel stale ones and register replacements. Do not attach unrelated human-created agents.

The plugin cannot reconstruct a whole working-and-settled turn missed while it was disabled, nor every agent's permission UI. On startup, requested status, or other task handling, use a bounded inventory and inspect changed or unexpectedly settled roles. Missing hooks must not leave tasks waiting indefinitely. Report an unavailable relay and offer repair instead of deploying worker callbacks.

Distinguish the sources of evidence:

- Human requests and unambiguous human transcript messages establish authorization and intent.
- Worker answers establish their conclusions; verify consequential claims against the relevant evidence.
- Git, GitHub, review artifacts, and verification establish changeset identity and results.
- Herdr and plugin notices establish runtime observations only.

Advance directly to the furthest supported state; do not replay ceremonial handoffs. An author's draft can already exist when you wake: confirm the approved scope, PR context, and current head, then start review. Do not interrupt authorized work merely because bookkeeping lags.

If a transcript is truncated, use available durable context or ask the same role once for its current result, head, and any missing evidence. A temporary Markdown result is appropriate when terminal output cannot be recovered. Do not demand a historical event sequence or JSON. If human authority remains uncertain, ask the human rather than accepting the worker's paraphrase as approval.

Changed code or human intent invalidates a prior pass; establish the current changeset before reusing review evidence. Update durable intent without making the author wait for record synchronization.

Reconcile old or contradictory status against the latest request, result, and next action on startup and wakes; do not carry it forward merely because it was saved. A finished request stays complete until new work is requested. Convert adopted records to the three states and remove redundant status flags/history while preserving evidence, ownership, and human decisions; no bulk rewrite is required. Replace one-shot watches with persistent ones when adopting a task, and retire old worker signaling instructions. Do not edit active sessions during package installation without a coordinated cutover.

## Cleanup

Cleanup is independent of task status. After the [recoverability audit](safety-and-escalation.md#cleanup), cancel only that task's watches and remove its owned linked worktree/workspace. Archive its record in the sibling archive directory, normally `.orchestrator/archive`, without adding a cleanup workflow state. Archive legacy cleaned records too. Normal status and recovery inspect active records only; historical recovery may consult the archive.
