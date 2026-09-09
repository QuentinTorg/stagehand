# Managed Agent Wake

This Herdr plugin wakes the Stagehand orchestrator after an explicitly watched
managed-agent turn changes from working to a settled state. It stores one-shot
watches and pending wakes under the configured workspace's ignored
`.orchestrator/wake/` directory.

The wake is only a runtime hint. Stagehand still reads the role output and
validates semantic events, authority, Git, GitHub, and Hunk state before changing
workflow state.

Install and configure it through the Stagehand
[installation guide](../../skills/orchestrating-development/references/installation.md).

Run its unit tests with:

```sh
python3 -m unittest discover -s plugins/stagehand-wake/tests
```
