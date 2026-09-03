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

For managed product roles, also record the required sandbox and approval policy. When guarded publication depends on unmatched commands remaining non-escalating, require workspace-write sandboxing with approval policy `never` and prohibit permissive overrides.

## Autonomous project configuration

For an autonomous project, record its durable charter inputs without copying the product specification:

```text
Project ID: <stable-project-id>
Project root: <absolute-root-containing-all-project-state>
Authoritative repository and document paths: <repository>: <paths>
Terminal milestone: <bounded-outcome-and-explicit-deferrals>
Decision-record directory and index: <paths-in-product-repository>

Repository integration map:
- <repository-name>: <canonical-checkout>; GitHub <host/owner/repository>; integration branch <branch>

Managed task-branch publisher: <stable-command-linked-to-stagehand-publisher>
Managed worktree rule source: <absolute-path-to-codex-managed-role.rules>

Worktree pool root: <absolute-path-beneath-project-root>
Maximum concurrently working managed agents: <count>
Maximum parallel heavy builds: <count-or-unlimited>
Normal monitoring interval: <seconds>
Healthy long-operation interval: <seconds>
```

State the exact initialization required for complete containing-repository worktrees, including how a project repository is placed into the build context before it becomes a registered submodule. Record `main` as read-only reference state, never an author or merge target. Autonomous authority must name one non-main integration branch per affected repository and one merge method.

Local policy may make the orchestrator the plan-approval and squash-merge authority for a chartered integration branch. It may not grant authors direct integration access, waive independent review or verification, authorize another merge strategy, or authorize any mutation of `main`.

State the autonomous monitoring cadence and the longer backoff for known builds or tests. A practical low-churn default is a batched lifecycle sweep every 240 seconds and a 600-second check for healthy long operations. Event delivery remains the fast path, while the cadence closes missed-signal gaps without repeatedly prompting workers.

State which network simulations are preauthorized. Prefer loopback, user-space transports, and isolated container bridges. Privilege escalation and host interface, route, firewall, namespace, tunnel, resolver, kernel, service, host-network container, capability, or device changes remain human-gated even when temporary. Privileged scenarios may be authored as manual evidence without being required or reported as passing.

State the context-rehydration bundle, deterministic sliding-lease duration, and consequential-transition gates. Every successful full rehydration must replace the prior deadline with one measured from its completion time. Conversation summaries must never own project state. Require complete rereads of the workspace bootstrap, orchestration skill and governing references, then current project/package/task records, applicable decisions, and active packages' cited product sections before the first mutation after activation, session resume, suspected compaction, or context uncertainty, and whenever the persisted due time elapses. Before package starts, plan approvals, specification decisions, finalization, merges, and repair/revert actions, require bounded validation of the affected records, heads, evidence, and cited product sections against the current checkpoint. Such a gate escalates to full rehydration only when due or when bounded validation exposes uncertainty. Stable watchdog ticks with a valid lease should not reload the complete product documentation corpus.

## Local command policy

Document environment-specific command conventions needed by installed approval rules, such as using a confirmed checkout as the command working directory. Do not use this section to grant broad destructive authority.
