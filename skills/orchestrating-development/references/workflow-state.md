# State and Wakeups

Read when dispatching work or recovering coordination. Workers do not read or write orchestration state.

## Durable record

Use the common [task-record.yaml](../assets/task-record.yaml) for all modes; omit unused fields. Keep active records in the configured directory, normally `.orchestrator/tasks`. This is a recovery note and dashboard input, not a checklist or permission system.

Record what a replacement coordinator needs: objective and intent reference, exact repository/target/branch/base, workspace and role identities, native session IDs when available, PRs, latest result/evidence, next action, and relevant human decisions. Preserve separate target identities for multi-repository changes; a submodule PR does not imply a meta PR.

Use `state.name: active` while work or human discussion continues and `complete` for a verified orchestration handoff, not necessarily a merge. `queued`, `closed`, and `cleaned` describe waiting, ended, and removed tasks. These are observations, not phases to visit. The board also accepts existing detailed state names.

Keep `state.summary` short (e.g. “Author fixing findings”), `next_role` for who acts next, and `next_action` for the concrete next step. Mark `attention_required` only for a human action and explain it in `attention_reason`; dependencies or active agents remain yellow. Runtime idle/done is not workflow completion.

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

Existing records remain usable; ignore obsolete counters and phase gates, preserving evidence, ownership, and human decisions. No bulk migration is required. Replace one-shot watches with persistent ones when adopting a task, and retire old worker signaling instructions. Do not edit active sessions during package installation without a coordinated cutover.

## Cleanup

After the [recoverability audit](safety-and-escalation.md#cleanup), cancel only that task's watches and remove its owned linked worktree/workspace. Archive the `cleaned` record in the sibling archive directory, normally `.orchestrator/archive`. Archive legacy cleaned records too. Normal status and recovery inspect active records only; historical recovery may consult the archive.
