# Installation

Stagehand's orchestration skill and Herdr rules are workspace-local. Workers need only their usual agent setup and the relevant Skilldex skills—no orchestration skill, event rules, or Hunk installation.

## Guided setup

Inspect before changing anything. Report what is ready, missing, or needs a user choice. Preview each remaining step with its exact source/destination, whether it copies, links, configures, or validates, and any required restart.

For an audit, offer to perform the missing setup. For a setup request, carry out authorized steps and report remaining human actions. Do not replace an existing file or link until its ownership and target are understood and the replacement is authorized.

The host needs Herdr, Git, GitHub CLI authentication for the relevant hosts, and Python 3. The optional board has a Python dependency documented in its own setup guide. Product agents retain their normal sandbox and approval settings.

## Workspace and skills

Use the selected agent's workspace instruction and skill-discovery mechanisms. The shared bootstrap is [AGENTS.md](../../../AGENTS.md); if the agent does not load it automatically, use its startup instructions or a thin loader that points to it rather than copying the workflow. Keep orchestration workspace-local, not globally available to workers.

For Codex, keep the tracked `.codex/skills/orchestrating-development` relative link and `.codex/rules/herdr.rules`. Other agents need equivalent local skill discovery and their own permission configuration; Codex rules do not configure other agents.

Copy [the local template](../../../templates/AGENTS.local.md) to the ignored `.local/AGENTS.md`, or link that file to a private configuration repository. Configure repository paths, hosts, initialization caveats, and model choices. Confirm `git check-ignore .local/AGENTS.md` succeeds. Never commit private configuration or credentials.

Load the Herdr skill before control operations. If it is not discoverable, run `herdr --skill` for version-matched bootstrap guidance, then expose the installed skill to the selected agent (for Codex, link it into this workspace's `.codex/skills/herdr`). Do not guess an npm/reference-checkout path or link an entire skills parent.

## Managed-role skills

Clone [Skilldex](https://github.com/QuentinTorg/skilldex) if needed, then install its skill directories individually where product agents discover them. For Codex:

```sh
mkdir -p ~/.codex/skills
ln -s /absolute/path/to/skilldex/skills/preparing-pull-requests ~/.codex/skills/preparing-pull-requests
ln -s /absolute/path/to/skilldex/skills/reviewing-code ~/.codex/skills/reviewing-code
ln -s /absolute/path/to/skilldex/skills/resolving-findings ~/.codex/skills/resolving-findings
```

Inspect existing destinations first. `writing-specifications` is optional and can be linked the same way. Do not install superseded review/feedback skills. These skills support plain review output; Hunk is not a prerequisite.

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

Validate instruction and skill discovery, enabled plugins, the consumer's exact target/root, and local configuration for each selected agent. Confirm Herdr can observe its lifecycle and read its output before relying on unattended handoffs. Check the agent's permission policy; for Codex:

```sh
codex execpolicy check --rules .codex/rules/herdr.rules --pretty herdr agent list
codex execpolicy check --rules .codex/rules/herdr.rules --pretty herdr workspace close w2
```

Inspection should be allowed; workspace closure forbidden. For Codex, restart sessions after rule changes; follow other agents' reload requirements for their setup. Run the relay and board unit tests before a live trial.

## Existing installations

Do not hot-swap active workers during package setup. Arrange a coordinated cutover: load the new skill, preserve active task evidence, replace old one-shot registrations with persistent watches, and tell existing workers once to stop sending workflow events. Fresh workers need no such instructions.

The former global `~/.codex/rules/orchestrating-development-events.rules` link is no longer needed. Inspect it and remove only that package-owned link when authorized; preserve customized rules or unrelated Hunk permissions. Existing Hunk installations and sessions need not be uninstalled or closed. New tasks use normal review responses.

This migration changes notifications, not product work or human authority. Keep private repository setup and cleanup caveats. Reconcile the active records before restarting any workflow; do not recreate already-existing PRs or discard completed review evidence.
