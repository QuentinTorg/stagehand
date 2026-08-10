# Managed workflow control block

Prepend this rendered block to every prompt the orchestrator sends a managed author or reviewer, including startup, recovery, draft creation, finding resolution, rereview, finalization, and post-review work.

```text
WORKFLOW task={{task_id}} role={{role}} orchestrator={{orchestrator_agent}} scope={{scope_version}} stage={{workflow_state}} allowed={{allowed_events}}
This routing contract persists until explicit release or task cleanup. Human discussion, silence, or no recent orchestrator message does not detach you; never substitute another endpoint.
At a workflow boundary, send exactly one allowed event with `herdr agent prompt {{orchestrator_agent}} '<single-line-json>'` and no `--wait`. Success requires exit success and type `agent_prompted` for that endpoint. Retry the identical payload once; after a second failure print `WORKFLOW_EVENT_FALLBACK <json>`, stop before the next stage, and wait for recovery.
On startup, begin your first response with `Workflow attached: {{task_id}} / {{role}} -> {{orchestrator_agent}}`.
```

Fill every field from the validated task record. `allowed_events` contains only the outcomes valid for the requested operation, including the role's blocker event. Do not send an unrendered block or leave placeholders for the managed agent to infer.
