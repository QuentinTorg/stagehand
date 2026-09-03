# Managed workflow control block

Prepend this rendered block to every prompt the orchestrator sends a managed author, reviewer, or worker, including startup, recovery, and later handoffs.

```text
WORKFLOW task={{task_id}} task_record={{task_record_path}} role={{role}} orchestrator={{orchestrator_agent}} authority={{authority_profile}} approval={{plan_approval_actor}} project={{project_id}} package={{package_id}} integration={{integration_branch}} publisher={{task_branch_publisher}} scope={{scope_version}} stage={{workflow_state}} allowed={{allowed_events}}
Work toward the stated outcome using sound engineering judgment. Resolve ordinary repository, tool, dependency, build, and optional-CI issues yourself when a safe in-scope path exists; ask for help only when authority or essential information is genuinely missing.
Stay inside this task and role. Never work on, target, push to, or merge `main` or the integration branch. Authors publish only through the named guard; reviewers never publish source or merge. Never use credentials, privilege elevation, or host network/system mutation.
At a workflow boundary, send one allowed event with `herdr agent prompt {{orchestrator_agent}} '<single-line-json>'` and no `--wait`. Retry once; after a second failure print `WORKFLOW_EVENT_FALLBACK <json>` and preserve your work for recovery.
On startup, begin your first response with `Workflow attached: {{task_id}} / {{role}} -> {{orchestrator_agent}}`.
```

Fill every field from the validated task record and local installation. Use `supervised`, `human`, and `none` for ordinary tasks; use the exact charter and package identities for autonomous-project tasks. Use `none` as the publisher for roles that may not publish. `allowed_events` contains only outcomes valid for the requested operation, including the role's blocker event. Do not send an unrendered block or leave placeholders for the managed agent to infer.
