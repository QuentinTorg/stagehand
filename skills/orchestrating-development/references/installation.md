# Installation

Stagehand's orchestration skill and Herdr rules are workspace-local. Workers need only their usual agent setup and the relevant Skilldex skills—no orchestration skill, event rules, or Hunk installation.

## Guided setup

Inspect before changing anything. Report what is ready, missing, or needs a user choice. Preview each remaining step with its exact source/destination, whether it copies, links, configures, or validates, and any required restart.

For an audit, offer to perform the missing setup. For a setup request, carry out authorized steps and report remaining human actions. Do not replace an existing file or link until its ownership and target are understood and the replacement is authorized.

The host needs Herdr, Git, GitHub CLI authentication for the relevant hosts, and Python 3. The optional board has a Python dependency documented in its own setup guide. Product agents retain their normal sandbox and approval settings.

## Agent-specific setup

Identify the agents used by the coordinator and workers. Load only their applicable setup reference:

- [Codex](setup-codex.md)

For an agent without a packaged reference, use its documented instruction/skill discovery, permission, and reload mechanisms to meet the requirements below. Do not copy another agent's configuration or duplicate the workflow.

## Workspace and skills

Use the selected agent's workspace instruction and skill-discovery mechanisms. The shared bootstrap is [AGENTS.md](../../../AGENTS.md); if the agent does not load it automatically, use its startup instructions or a thin loader that points to it rather than copying the workflow. Keep orchestration workspace-local, not globally available to workers.

Copy [the local template](../../../templates/AGENTS.local.md) to the ignored `.local/AGENTS.md`, or link that file to a private configuration repository. Configure repository paths, hosts, initialization caveats, and model choices. Confirm `git check-ignore .local/AGENTS.md` succeeds. Never commit private configuration or credentials.

Load the Herdr skill before control operations. If it is not discoverable, run `herdr --skill` for version-matched bootstrap guidance, then expose the installed skill to the selected agent. Do not guess an npm/reference-checkout path or link an entire skills parent.

## Managed-role skills

Clone [Skilldex](https://github.com/QuentinTorg/skilldex) if needed, then install `preparing-pull-requests`, `reviewing-code`, and `resolving-findings` individually where product agents discover skills. Inspect existing destinations first. `writing-specifications` is optional. Do not install superseded review/feedback skills. These skills support plain review output; Hunk is not a prerequisite.

## Agent Wake Relay

Link the bundled plugin and register this exact control workspace:

```sh
herdr plugin link /absolute/path/to/stagehand/plugins/agent-wake --enabled
/absolute/path/to/stagehand/plugins/agent-wake/agent-wake configure \
  --state-root /absolute/path/to/stagehand/.orchestrator/wake \
  --target workflow_orchestrator
herdr plugin list
/absolute/path/to/stagehand/plugins/agent-wake/agent-wake status \
  --state-root /absolute/path/to/stagehand/.orchestrator/wake
```

The plugin can be installed globally; it watches only explicitly registered source agents. The coordinator registers persistent watches as it starts roles. See [relay usage and limits](../../../plugins/agent-wake/README.md). Do not install callbacks or global Herdr permissions in worker sessions.

Reserve `workflow_orchestrator` for exactly one live controller. Inspect any existing owner before naming a new one; maintenance agents must not claim it or consume its wakes.

## Status pane and validation

Follow [status-board setup](../../../plugins/status-board/README.md#setup) to install its dependency and link the plugin. The orchestrator opens or reuses one board beside its conversation, using the configured task directory. Text status remains available if the board is unavailable.

Validate instruction and skill discovery, enabled plugins, the consumer's exact target/root, and local configuration for each selected agent. Confirm Herdr can observe its lifecycle and read its output before relying on unattended handoffs. Validate permissions and reload using that agent's setup instructions. Run the relay and board unit tests before a live trial.

## Existing installations

Do not hot-swap active workers during package setup. Arrange a coordinated cutover: load the new skill, preserve active task evidence, replace old one-shot registrations with persistent watches, and tell existing workers once to stop sending workflow events. Fresh workers need no such instructions.

Use the applicable agent setup reference for obsolete installation cleanup. Existing Hunk installations and sessions need not be uninstalled or closed. New tasks use normal review responses.

This migration changes notifications, not product work or human authority. Keep private repository setup and cleanup caveats. Reconcile the active records before restarting any workflow; do not recreate already-existing PRs or discard completed review evidence.
