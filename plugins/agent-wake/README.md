# Agent Wake Relay

Wake a controller when a registered Herdr agent starts/resumes or stops working—without polling agents or asking workers to send callbacks. Useful for coding, review, research, or human-led conversations that a coordinator should follow.

The relay matches the source workspace, pane, agent name, and available native session identity. It queues a durable notice, defers delivery while the controller is busy, coalesces pending turns, and bounds notification retries. It never interprets output, approves commands, or decides that a task succeeded.

The plugin ships inside Stagehand but has no Stagehand-specific task schema. Keys and metadata are opaque consumer context.

## Setup

```sh
herdr plugin link /path/to/stagehand/plugins/agent-wake --enabled
/path/to/stagehand/plugins/agent-wake/agent-wake configure \
  --state-root /path/to/controller-state/wake --target controller_agent
```

Use a unique live controller name and a private durable state directory. Only explicitly registered source agents are watched; installing globally does not attach other agents.

## Watch an agent

After the source agent is running, register it before sending work:

```sh
/path/to/stagehand/plugins/agent-wake/agent-wake arm --persistent \
  --state-root /path/to/controller-state/wake --key work-42 \
  --workspace-id w2 --workspace-label feature-42 \
  --pane w2:p1 --agent worker_agent --metadata '{"role":"worker"}'
```

A persistent watch reports `working` and subsequent idle/done/blocked transitions, including turns started directly by a human. It remains active until cancelled. Omit `--persistent` for a backward-compatible, stop-only one-shot watch.

The controller receives `HERDR_AGENT_WAKE` followed by a JSON array containing the wake ID, key, metadata, workspace, pane, and observed status. The worker does not generate this message.

- A `working` notice is activity, not a request to dispatch, evidence of approval, or proof of who submitted input. Reconcile already-known activity without interrupting the worker. A stop may mean a question, permission request, findings, or success; inspect current evidence.
- `ack --state-root <root> --wake <id>` consumes that notice, not the persistent subscription.
- `cancel --state-root <root> --watch <id>` removes the subscription and its queued notices.
- `status --state-root <root>` lists registrations and the durable inbox.
- `flush` performs one recovery snapshot and delivery attempt for configured consumers.

Repeated registration of the same identity is idempotent. A changed mode or native session requires cancellation and registration after the controller reconciles ownership. Cancel before task cleanup or role retirement.

On startup, a watch can anchor to the foreground agent process until Herdr exposes its native session ID; that first ID does not require re-registration. Registration also checks for work that finished during setup. Use `--observed-working` only when you actually observed that turn running; an already-idle agent alone is not evidence of completion.

## Delivery limits

Each watch retains at most one notified-but-unacknowledged wake plus one coalesced pending wake. Pending updates reflect the latest observed state, not a complete event history; a rapid stop can replace an undelivered start. Duplicate working snapshots and idle/done focus changes do not create new notices. Acknowledging an older wake cannot erase a later transition. Undelivered notifications stop retrying after three failed prompt attempts; inspect the retained error, reconcile the source, and acknowledge after handling it. Busy-controller deferral does not spend retries.

Herdr startup runs a bounded recovery flush. A turn entirely missed while hooks were disabled cannot be reconstructed from lifecycle alone; consumers should reconcile on restart and requested status. Session identity is checked when Herdr exposes it. Human typing can still race with terminal prompt delivery; the consumer must preserve human text separately from an appended wake.

The relay does not install a timer, launch an agent, approve a permission request, or require a worker skill. It depends on Herdr recognizing the agent's runtime state.

## Tests

```sh
python3 -m unittest discover -s plugins/agent-wake/tests
```
