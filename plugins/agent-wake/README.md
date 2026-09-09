# Agent Wake Relay

Agent Wake Relay lets one Herdr agent react when another agent's dispatched turn
settles without polling or requiring the worker to remember a callback. A
controller arms a one-shot watch before prompting a worker. After the worker
changes from working to idle, done, or blocked, the plugin durably queues a
compact wake prompt for the controller.

The plugin is useful for orchestrators, parent-worker workflows, and other agent
controllers. It provides exact pane and agent matching, duplicate suppression,
busy-controller deferral, bounded retries, and startup recovery. It deliberately
does not interpret the worker's output: settlement is a reason to inspect the
worker, not proof that its task succeeded.

The plugin currently ships inside Stagehand, which uses the opaque watch metadata
to associate wakes with workflow tasks and roles. Its public contract does not
depend on Stagehand and can be packaged separately later.

Install and configure the bundled copy through the Stagehand
[installation guide](../../skills/orchestrating-development/references/installation.md).

## General use

Link the plugin and register a durable state directory with the agent that should
receive wakes:

```sh
herdr plugin link /path/to/stagehand/plugins/agent-wake --enabled
/path/to/stagehand/plugins/agent-wake/agent-wake configure \
  --state-root /path/to/controller-state/wake --target controller_agent
```

Before dispatching work, arm the source agent's exact Herdr identity. `--key` and
`--metadata` are opaque consumer context returned unchanged in the wake:

```sh
/path/to/stagehand/plugins/agent-wake/agent-wake arm \
  --state-root /path/to/controller-state/wake --key work-42 \
  --workspace-id w2 --workspace-label feature-42 \
  --pane w2:p1 --agent worker_agent --metadata '{"role":"worker"}'
```

The target receives `HERDR_AGENT_WAKE` followed by a JSON array. Inspect the
source agent, then run `ack`; use `cancel` when dispatch fails and `status` during
recovery. Each subcommand provides argument help.

Run its unit tests with:

```sh
python3 -m unittest discover -s plugins/agent-wake/tests
```
