# Autonomous Project Control

## Sections

- [Authority and source documents](#authority-and-source-documents)
- [Project and package records](#project-and-package-records)
- [Context rehydration and durable progress](#context-rehydration-and-durable-progress)
- [Scheduling and scope reservations](#scheduling-and-scope-reservations)
- [Low-frequency monitoring and missing signals](#low-frequency-monitoring-and-missing-signals)
- [Workspace leases](#workspace-leases)
- [Branch and pull-request lifecycle](#branch-and-pull-request-lifecycle)
- [Specification evolution and decision records](#specification-evolution-and-decision-records)
- [Verification and review](#verification-and-review)
- [Portable network simulation](#portable-network-simulation)
- [Convergence and recovery](#convergence-and-recovery)
- [Check-ins and resumption](#check-ins-and-resumption)
- [Project completion](#project-completion)

## Authority and source documents

Autonomous-project mode exists only inside a validated project charter based on [project-record.yaml](../assets/project-record.yaml). The charter is a capability boundary, not general permission. Confirm its project ID, authorization reference, allowed repositories, project root, integration branch per repository, terminal milestone, deferred gates, merge method, and agent limit before any project mutation.

The approved design specification defines product intent, externally visible behavior, architecture, and ownership. The approved implementation plan defines package boundaries, dependency order, verification, and delivery. Read their complete relevant sections before materializing the graph, assigning a package, approving an author plan, reviewing, or merging. Record the exact source commit and section anchors. Donor code, existing behavior, and agent preference are evidence only; none silently override the documents.

The role title is **Autonomous Project Integration Director**. The role owns scheduling, bounded plan approval, coordination decisions, evidence validation, integration-branch merges, recovery, and resource stewardship. It does not implement product code or perform the independent review that gates its merge.

The orchestrator is the plan approval actor for every chartered package. It must compare the author's cited plan with the package objective, authoritative sections, neighbor contracts, exclusions, reservations, dependency direction, reusable-test design, verification matrix, and completion criteria. Approve by returning a fresh implementation control block only when all agree. Otherwise return specific bounded corrections and require a revised `plan-proposed`; do not silently rewrite the author's plan. This replaces the routine human plan checkpoint. Ask the human only when the plan requires authority outside the charter, such as credentials, destructive host mutation, production-security acceptance, physical deployment, privileged host-network execution, or any operation involving `main`.

## Project and package records

Create one project record and one [project-work-package-record.yaml](../assets/project-work-package-record.yaml) per plan node. Keep mutable records under `.orchestrator/projects/<project-id>/`; never commit orchestration runtime state to a product repository.

Materialize, rather than reinterpret, the implementation plan. Every package record carries:

- objective and authoritative document sections;
- prerequisite packages, decisions, and external artifacts;
- owned repositories, paths, contracts, and shared test infrastructure;
- neighbor contracts and explicit exclusions;
- verification matrix and required completion evidence;
- one delivery entry per repository PR; and
- current reservations, convergence counters, decisions, and state.

A plan package may require several repository PRs or task worktrees. Preserve one package identity and its cross-repository merge order; do not mark it complete because one constituent PR merged.

Use these project/package states:

| State | Meaning |
| --- | --- |
| `chartered` / `planned` | Recorded but not yet proven eligible |
| `blocked` | A prerequisite, decision, external artifact, or conflict is unresolved |
| `eligible` | Prerequisites and reservations permit scheduling |
| `active` | An author, reviewer, recovery role, build, or PR is active |
| `merge-ready` | Every exact-head review and verification gate for the next delivery passed |
| `integrating` | The guarded squash merge is in progress |
| `integrated` | All package deliveries merged and post-merge evidence passed |
| `repairing` | A merged integration regression has a bounded repair or revert package |
| `deferred` | The charter explicitly excludes the gate from its terminal milestone |
| `complete` | The terminal milestone and aggregate evidence are satisfied |
| `paused` | Human check-in prevents new scheduling or merges until resume |

Persist every transition with its evidence. Herdr lifecycle and agent prose are observations, not package completion proof.

## Context rehydration and durable progress

The durable project graph, package records, task records, decision index, integration heads, reservations, verification evidence, and live artifact state are the controller's memory. Conversation history and compaction summaries are navigation aids only.

Perform a complete rehydration before the first project mutation after controller activation, controller-session resume, a detected or suspected context compaction, a human resume after pause, or any uncertainty about instructions or state. Also rehydrate when the recorded skill or source-document commit differs from the current one.

Do not depend on detecting compaction. The project record carries a deterministic full-rehydration lease no longer than 3,600 seconds; local policy may shorten it. Every watchdog sweep compares current time with `rehydration.next_full_due_at`; a missing, invalid, or elapsed value makes rehydration due. Never schedule the next watchdog check later than that deadline, even when a healthy long operation would otherwise use a longer backoff. Every successful full rehydration, whatever its trigger, replaces the prior deadline with a new one measured from that rehydration's completion time. Clock ambiguity or rollback makes the lease invalid rather than extending it.

While the lease remains current, perform bounded transition validation immediately before any of these consequential gates:

- creating, publishing, scheduling, starting, replacing, or materially rescoping a package or integration branch;
- approving or revising an author's implementation plan;
- authorizing a specification change, ADR, package invalidation, or scope-version change;
- authorizing reviewer finalization;
- invoking a guarded merge; or
- creating or integrating a repair or revert.

For bounded transition validation, reread the exact affected project/package/task records, referenced decisions, current heads and evidence, and only the authoritative design and implementation-plan sections cited by the affected package. Reconcile those sources against the current full-rehydration checkpoint. Then persist the gate action, affected package/repository identities, and exact relevant heads before executing the transition. One validation may cover one explicitly recorded atomic batch of nonconflicting package starts. If an identity changes, the gate is stale and must be validated again. If the lease is due or this narrow validation reveals missing, contradictory, or uncertain context, complete full rehydration before proceeding.

Use this rehydration order:

1. reread the complete workspace `AGENTS.md`, `.local/AGENTS.md`, `.local/workspace.yaml`, orchestration `SKILL.md`, project-control, workflow-state, and safety references;
2. reread the active project record, the records for active, blocked, and next-candidate packages, and every linked active task record;
3. reread the checked-in decision index and each decision referenced by those packages;
4. reread the exact authoritative design and implementation-plan sections cited by those packages, plus any neighbor-contract sections needed to interpret them;
5. reconcile integration heads, branches, PRs, checks, worktrees, reservations, Herdr roles, Hunk sessions, and current verification evidence; and
6. increment the rehydration generation and persist the reason, completion time, next full due time, controller session identity when available, current Stagehand commit, source-document commit, and package-state snapshot time in the project rehydration checkpoint.

If any source disagrees, preserve state and resolve it under the normal authority rules before mutation. Never fill a missing detail from a conversation summary, replay a completed transition, or assume a previous approval survived a changed scope/head. A rehydration checkpoint proves that sources were reread; it does not prove their conclusions or replace evidence.

Do not reload the entire product documentation corpus on every four-minute watchdog tick or consequential transition while the deterministic lease remains valid. That wastes context and can cause further compaction. During a stable monitoring loop, read due records and bounded evidence only. Full rehydration returns when the hourly lease expires or a recovery condition above occurs; each author plan, specification decision, review, and merge rereads only its cited authoritative sections and exact current evidence as bounded transition validation.

The package graph is the progress ledger. Derive status from recorded package state and evidence, never from a prose percentage. A package is not advanced until the exact transition evidence is persisted; a project is not complete until every required graph node and terminal evidence gate is satisfied. After materializing the implementation plan, ensure every graph node has a package record before starting the first author.

## Scheduling and scope reservations

Reconcile the entire active project before scheduling. A package is eligible only when each prerequisite is integrated or explicitly deferred by the charter, every required decision exists, external artifacts are verified, and its reservations do not conflict with active work.

Reserve affected repositories, paths, schemas, generated outputs, public interfaces, configuration, and shared test infrastructure at the narrowest reliable granularity. Two packages conflict when either could redefine the other's contract, generated source, integration base, build configuration, deployment surface, or authoritative fake. A different filename does not prove independence.

Enforce the project record's working-agent limit across authors, reviewers, and recovery workers. Idle persistent roles do not consume a working slot; a role with an active turn does. Apply any separately recorded build semaphore. Prefer critical-path packages and useful independent branches, but leave capacity unused rather than invent speculative work.

The orchestrator may split a plan node only to create reviewable deliveries that preserve the package's objective, contracts, and completion criteria. It may not use decomposition to make a partial result appear complete or allow two authors to own the same decision surface.

## Low-frequency monitoring and missing signals

Semantic events are the fast path, not the only recovery path. While an autonomous project has active managed roles, maintain the monitoring and healthy-long-operation intervals recorded by the charter. Persist the last sweep, each role's last observed lifecycle and output digest, and its next check time so controller restarts do not cause a burst of duplicate polling.

At each due sweep:

1. inspect active Herdr roles in one bounded inventory and compare lifecycle with the task/package wait condition;
2. do not read or prompt a healthy `working` role unless its long-operation check is due, its artifacts contradict the record, or it exceeded a recorded notice threshold;
3. inspect a bounded recent transcript for an unexpected `idle`, `done`, `blocked`, or `unknown` role, or for a role whose expected event is overdue;
4. recover and validate a complete delivered event or `WORKFLOW_EVENT_FALLBACK` before asking the role for anything;
5. when the current role conclusion is still missing, send one fresh control block requesting only the exact current-boundary event and record the attempt; and
6. reconcile artifacts and advance only to the furthest independently proven state, then schedule newly eligible work.

Use `herdr agent wait <role> --timeout <milliseconds>` when one role is near a boundary and a bounded wait avoids another model turn. Otherwise wait until the earliest recorded next check and sweep roles together. A timeout is a cadence tick, not evidence of failure. Never repeatedly ask for progress, reread full transcripts, poll GitHub for unchanged state, or wake healthy roles merely to prove the controller is active. Back off rather than accelerate during known expensive builds.

Continue this event-first, watchdog-backed loop until the terminal milestone, an explicit check-in pause, or a genuine out-of-charter blocker. The autonomous kickoff itself authorizes attached monitoring; no additional human request is required to keep reconciling overnight.

## Workspace leases

Product work uses complete containing-repository worktrees when builds require the meta-repository context. Keep every checkout, worktree, task record, and scratch artifact beneath the charter's project root. Initialize submodules and any not-yet-registered project repository exactly as local configuration specifies before starting the author.

One workspace lease belongs to one active package lineage. Related author, reviewer, fix, and repair turns may reuse it. Never place independent active packages in one worktree.

A settled workspace may return to the reusable pool only after verifying:

1. its owning package deliveries and decisions are durable in recorded branches, PRs, or merge commits;
2. all repositories and initialized submodules contain no unrecorded tracked or untracked work;
3. no stateful agent, build, server, editor, or permission interaction must survive;
4. its integration and task branches are recorded and recoverable;
5. submodule pins and containing-repository changes match the completed package disposition; and
6. ownership is unique and the next lease can be initialized from its exact integration head without reset, clean, or data loss.

If any check fails, preserve the workspace. Reuse is a new audited lease, not casual branch switching. Never reset, clean, overwrite, or discard state to make a pool slot available.

## Branch and pull-request lifecycle

For each affected repository, the project record names one non-main integration branch. No agent may implement on, commit to, push to, merge into, or target an author pull request at `main`. Read-only fetch, inspection, and ancestry comparison are permitted only to verify a base or create a missing integration branch.

When the integration branch is absent, only the orchestrator may create and publish it from the verified charter base. This initial publication is the sole direct integration-branch push. Afterward:

1. record the exact current remote integration head;
2. create the author's task branch from that commit;
3. record exact-head publication authority and allow the author to publish only its task branch through the managed task-branch guard;
4. require a PR whose base is the integration branch;
5. reject or correct a changed base before review;
6. independently review and verify the exact PR head; and
7. let only the orchestrator invoke the guarded squash-merge script.

Never use merge commits, rebase merge, auto-merge, merge queues, administrator bypass, force push, or direct integration updates. The guard requires the invoking pane to own `workflow_orchestrator`, canonical project/package record paths, a current rehydration lease, a `guarded-merge` transition checkpoint naming the exact package/repository/head, and agreement among the project, package, checkpoint, and current Stagehand identities. Before invoking `gh pr merge`, it queries every page of active rules for the exact base and rejects merge-queue governance; an unavailable or malformed rules query fails closed. It also requires the PR to be immediately clean and mergeable. After the script returns, independently verify the PR is merged, the reported merge commit is reachable from the remote integration branch, and the integration branch gained exactly one squash commit for that PR. Store the merge commit in the delivery record before unlocking successors.

The orchestrator has no authority to create, approve, or merge a promotion to `main`. Final promotion is external to this autonomous charter.

## Specification evolution and decision records

When implementation evidence conflicts with the approved documents, stop only the affected packages and continue unrelated eligible work. Determine whether the issue is an implementation defect, a clarification that preserves behavior, or a material product/architecture decision.

The orchestrator may authorize the smallest coherent specification correction inside the charter. For a material correction:

1. create a checked-in ADR from [project-decision-record.md](../assets/project-decision-record.md) in the product repository's configured decision directory;
2. identify the prior assumption, evidence, credible alternatives, decision, rationale, consequences, affected packages, and validation;
3. update every owning design and implementation-plan section in the same PR;
4. invalidate or revise package records whose scope, prerequisites, contracts, tests, or merge order changed;
5. require independent review of the decision and documentation just like code; and
6. merge the decision before or atomically with its first dependent implementation.

Maintain a checked-in decision index ordered by ADR ID. Project records reference ADRs and their merge commits. Do not turn ordinary implementation detail into an ADR, and never hide a material divergence only in orchestration state, chat, a PR body, or code comments.

## Verification and review

Authors must base their plans on the cited design and implementation-plan sections. Each PR description carries the package objective, owned scope, exclusions, document anchors, reusable-test changes, exact verification commands, results, limitations, and related decisions.

Mocks, fakes, fixtures, scenario drivers, and simulation harnesses are maintainable product test infrastructure. Extend the shared contract-level facility whenever one exists. A new fake must have a named owner, bounded behavior, documented contract, deterministic controls, and its own tests. It must not import the production internals it replaces or exist only in an untracked script, temporary directory, or agent transcript.

The independent reviewer holds authors to the documented intent and evaluates:

- correctness, failure handling, bounded resource behavior, and exact contract conformance;
- meaningful unit, adapter, contract, integration, install, and simulation evidence required by the package;
- clean ownership and dependency direction, with functionality placed in its responsible component;
- no business logic bleeding across process, transport, schema, platform, or UI layers;
- no duplicated contract, speculative framework, premature generalization, dead compatibility layer, or review-obscuring refactor;
- maintainable naming, comments that preserve intent, operational diagnostics, packaging, deployment configuration, and documentation; and
- agreement among the approved specification, implementation plan, schemas, code, fakes, tests, and observed behavior.

Before `merge-ready`, independently verify the exact reviewed head, required CI and local evidence, all package completion criteria, specification alignment, and required ADRs. A passing reviewer event or green CI alone is insufficient.

## Portable network simulation

Prefer deterministic process-local sockets, loopback endpoints, ephemeral ports, in-process transports, and repository-defined isolated container bridges that need no host networking capability. These tests are portable, rerunnable completion evidence. A container test is not automatically safe: host networking, privileged mode, added network capabilities, device access, macvlan/ipvlan, or host service mutation remains privileged host-network work.

Managed agents must never invoke `sudo`, `su`, `pkexec`, enter credentials, or attempt an equivalent privilege escalation. Without a specific human-approved procedure they also must not create or modify host interfaces, routes, firewall rules, network namespaces, TUN/TAP devices, DNS/resolver state, kernel network settings, network services, or persistent daemons. This prohibition includes temporary changes; reversibility does not supply authority.

An author may implement a useful scenario that truly requires privileged host-network configuration, but must isolate it behind an explicit `manual-privileged-network` classification, document prerequisites, state inspection, expected effects, rollback, and non-execution status, and test all separable logic without privilege. The orchestrator records it as deferred manual evidence rather than requiring it to pass the proof-of-concept gate. It may be executed only after the human approves the exact commands and cleanup plan. Never claim an unexecuted scenario passed or let it replace portable contract, adapter, and integration coverage.

## Convergence and recovery

Autonomous mode has no arbitrary review-round ceiling. It still forbids unbounded iteration. Track repeated material findings, consecutive rounds without a relevant diff or new evidence, incompatible author/reviewer conclusions, stale heads, and repeated role/event failures.

On loss of convergence, inspect evidence once and choose the least disruptive effective action: clarify the package contract, mediate a specific author/reviewer disagreement, narrow a repair, resume or replace a stalled role in the same recoverable workspace, or create a separately reviewed repair/revert PR. Do not add agents to seek a preferred answer, broaden scope, or rerun unchanged work indefinitely.

A bad integration merge never authorizes direct branch repair. Freeze affected successors, create a bounded repair or revert task from the current integration head, require the normal author/reviewer/evidence loop, and squash-merge its PR through the guard.

Continue independent eligible work while one branch is blocked. If no safe progress remains, persist the exact blockers and finish with a project report rather than fabricating completion.

## Check-ins and resumption

A human progress request interrupts scheduling. First reconcile project, package, GitHub, Git, Herdr, Hunk, build, and evidence state. Set the project to `paused`, allow already-running nondestructive operations to reach a safe boundary, and start no new agents, reviews, merges, or packages.

Report completed and active packages, dependency blockers, integration heads, open PRs, active-agent count, important decisions, verification status, risks, and the projected next critical-path actions. Do not require the human to disposition ordinary project decisions already delegated by the charter.

Resume only after an explicit human request. Reconcile again, clear the pause, recover existing roles and workspaces before creating replacements, and schedule from the current graph without duplicating work or replaying merges.

## Project completion

Do not equate exhausted plan nodes with success. The project reaches its terminal milestone only when:

- every required package is integrated and every deferred package matches an explicit charter gate;
- all integration heads and cross-repository pins are recorded and mutually compatible;
- clean build, installation, static, unit, adapter, contract, integration, and deterministic simulation evidence is current;
- deployment configuration, operational diagnostics, recovery behavior, and documentation are usable;
- specifications, implementation plans, schemas, code, shared fakes, and tests agree;
- all material decisions are indexed and reviewable; and
- no known material correctness, maintainability, boundary, or deployment defect remains hidden as follow-up.

Produce a final evidence and decision report. Completion grants no authority to promote or merge any repository to `main`.
