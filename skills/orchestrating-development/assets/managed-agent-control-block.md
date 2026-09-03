# Managed workflow control block

Prepend this rendered block to every prompt the orchestrator sends a managed author, reviewer, or worker, including startup, recovery, and later handoffs.

```text
WORKFLOW task={{task_id}} task_record={{task_record_path}} role={{role}} orchestrator={{orchestrator_agent}} authority={{authority_profile}} approval={{plan_approval_actor}} project={{project_id}} package={{package_id}} integration={{integration_branch}} publisher={{task_branch_publisher}} scope={{scope_version}} stage={{workflow_state}} allowed={{allowed_events}}
This routing contract persists until explicit release or task cleanup. Human discussion, silence, or no recent orchestrator message does not detach you; never substitute another endpoint.
The authority, approval actor, project, package, integration branch, and publisher are literal boundaries. `none` means no project/package/integration or publication authority. Never infer broader authority from repository access or credentials. Managed roles never run `git push` or mutating `gh` commands directly; an author publishes and creates the initial draft only through the named guard after the orchestrator records the exact authorized head and draft permission.
Never invoke privilege elevation or mutate host network/system configuration. If required evidence needs either, report the exact boundary and leave execution to a human-approved procedure.
At a workflow boundary, send exactly one allowed event with `herdr agent prompt {{orchestrator_agent}} '<single-line-json>'` and no `--wait`. Success requires exit success and type `agent_prompted` for that endpoint. Retry the identical payload once; after a second failure print `WORKFLOW_EVENT_FALLBACK <json>`, stop before the next stage, and wait for recovery.
On startup, begin your first response with `Workflow attached: {{task_id}} / {{role}} -> {{orchestrator_agent}}`.
```

Fill every field from the validated task record and local installation. Use `supervised`, `human`, and `none` for ordinary tasks; use the exact charter and package identities for autonomous-project tasks. Use `none` as the publisher for roles that may not publish. `allowed_events` contains only outcomes valid for the requested operation, including the role's blocker event. Do not send an unrendered block or leave placeholders for the managed agent to infer.
