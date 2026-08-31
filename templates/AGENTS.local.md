# Local Orchestration Configuration

Copy this template to `.local/AGENTS.md`, or place a symbolic link there to a file in a private configuration repository. Keep credentials and secret values out of this file.

## Human workflow preferences

Task authorization, implementation-plan approval, pull-request finalization, and merge ownership are defined by the orchestration skill. Do not restate them here.

Record only choices delegated to local policy, such as the preferred merge interface and strategy, standing draft-state policy for post-readiness changes, or stricter local limits.

## Repository resolution

List allowed location roots as hints, then map every preconfigured repository to one exact canonical checkout. A root does not authorize arbitrary scanning or mutation.

```text
Location roots:
- <absolute-root>: <purpose>

Configured repositories:
- <name>: <absolute-checkout>

GitHub hosts:
- <hostname>
```

State how the orchestrator should handle an unconfigured or ambiguous repository. Prefer explicit human confirmation over filesystem guessing.

## Primary checkout policy

Document expected primary branches and whether a clean, ancestry-verified primary checkout may be fast-forwarded after fetching. Specify any stricter preservation requirements for local state.

## Repository-specific initialization

For each exceptional repository, document only the non-obvious preparation the orchestrator must perform before launching an author:

- worktree or submodule initialization;
- target repository, remote, base branch, and branch rules;
- required remote overrides that must not modify tracked configuration;
- containing-repository pointer policy; and
- cleanup exceptions delegated by the generic workflow.

Leave product build selection and product-repository instructions to the author unless orchestration must perform them before launch.

## Managed-agent defaults

Record the preferred model and reasoning effort for newly launched agents. State whether inheritance is acceptable and how explicit task-specific human choices override the default.

## Local command policy

Document environment-specific command conventions needed by installed approval rules, such as using a confirmed checkout as the command working directory. Do not use this section to grant broad destructive authority.
