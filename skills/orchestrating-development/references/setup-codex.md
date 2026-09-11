# Codex Setup

Read only when configuring Codex as the coordinator or a worker. Follow the shared [installation procedure](installation.md); this reference supplies only Codex-specific paths, permissions, and reload steps.

## Instruction and skill discovery

The coordinator loads the repository's `AGENTS.md`. Keep the tracked `.codex/skills/orchestrating-development` relative link to the bundled skill; do not install orchestration globally. Link the installed Herdr skill directory individually into this workspace's `.codex/skills/herdr` after locating it through the shared setup procedure.

For workers, link the required Skilldex skills individually into the user skill directory. For the existing `.codex/skills` layout:

```sh
mkdir -p ~/.codex/skills
ln -s /absolute/path/to/skilldex/skills/preparing-pull-requests ~/.codex/skills/preparing-pull-requests
ln -s /absolute/path/to/skilldex/skills/reviewing-code ~/.codex/skills/reviewing-code
ln -s /absolute/path/to/skilldex/skills/resolving-findings ~/.codex/skills/resolving-findings
```

Inspect destinations before linking; preserve working installations. Confirm discovery with the installed Codex version: [current skill documentation](https://developers.openai.com/codex/skills) describes `.agents/skills` for repository and user discovery. Where required, use those destinations for individual links rather than replacing this checkout's working links. `writing-specifications` is optional.

## Permissions and reload

Keep the tracked `.codex/rules/herdr.rules` workspace policy. Project-local rules require a trusted project configuration; see [Codex rules](https://developers.openai.com/codex/rules). These are coordinator permissions, not global worker permissions.

Validate the packaged rules without executing the example commands:

```sh
codex execpolicy check --rules .codex/rules/herdr.rules --pretty herdr agent list
codex execpolicy check --rules .codex/rules/herdr.rules --pretty herdr workspace close w2
```

Inspection should be allowed; workspace closure forbidden. Restart Codex after rule changes. Verify required skills are discoverable; if newly installed skills do not appear, restart the session.

## Existing installations

The former global `~/.codex/rules/orchestrating-development-events.rules` link is no longer needed. Inspect it and remove only that package-owned link when authorized; preserve customized rules and unrelated Hunk permissions.
