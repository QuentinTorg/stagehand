# Optional status reporter

The ordinary Stagehand workflow remains the default. An optional observer provides richer dashboard context without directing work or changing authoritative task records.

## Responsibilities

| Component | Owns |
| --- | --- |
| Orchestrator | Task intent, ownership, decisions, dispatch, and durable handoffs |
| Reporter | Explanations of recent work, current review coverage, next actor/action, and human attention |
| Wake relay | Independent subscriptions and inboxes; bounded, coalesced delivery |
| Dashboard | Settings, reporter launch, freshness checks, presentation, and fallback |

The reporter can read assigned agents and the orchestrator, but cannot message or control them. No worker instruction changes are needed. The orchestrator retains recovery records but need not compose dashboard summaries while reporting is enabled.

## Workspace and configuration

The reporter runs in a separate tab of the orchestrator's Herdr workspace, with a dedicated private working directory outside the Stagehand checkout. Its own `AGENTS.md` defines observation-only behavior. Its only installed workspace skill is a symlink to the configured Herdr skill; it does not load Stagehand's orchestration instructions.

The user chooses the Herdr harness kind and native launch arguments. The initial Codex preset is `gpt-6-luna` with medium reasoning. Other harnesses use their own arguments, not assumed Codex flags. Enabling reporting explicitly authorizes launching one observer; failures leave its pane inspectable rather than creating replacements.

## Updates and fallback

Workers and the orchestrator are watched through a separate wake-relay consumer. The reporter never acknowledges the orchestrator's inbox. Its own activity is excluded, preventing wake loops. Pending events coalesce while it works; it does not continuously poll.

Reports live in the reporter's private workspace. They refer to observed task and agent fingerprints. New task intent, changed identities, or later worker activity invalidates an old report. Stale or missing reports leave the existing dashboard status intact and label any retained explanation as previous information.

Turning reporting off cancels only its subscriptions. The original task records, controller binding, worker subscriptions, and message drafts remain unchanged. The reporter tab remains available for inspection; disabling does not interrupt an active agent. There is no automatic restart or model promotion.

See the [board setup and controls](../plugins/status-board/README.md#optional-status-reporter) for installation and use.
