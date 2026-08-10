# Preparing Pull Requests

## Skill Contract Overview

The preparing-pull-requests skill creates the structured draft pull request used for independent review and later finalizes that same artifact after a successful review and explicit developer authorization. It ensures that ordinary requests such as “create a draft PR” reliably produce the context required by the next agent without turning the full workflow into an always-on prompt.

The skill implements the actions defined by [`50-pull-request-lifecycle.md`](./50-pull-request-lifecycle.md). It does not implement code, conduct review analysis, resolve findings, approve, or merge.

## Explicit Trigger

The skill activates when the developer explicitly asks to:

- create, open, or prepare a draft pull request for a completed changeset;
- prepare a branch for independent review;
- finalize the description of a successfully reviewed pull request; or
- mark a reviewed pull request ready after explicit authorization.

Mentioning, inspecting, summarizing, or reviewing a pull request is not sufficient. Requests to post a code review, address comments, check CI, or merge belong elsewhere. If the requested mode or authorization is ambiguous, the skill clarifies before mutating GitHub state.

## Common Inputs and Validation

Before either mode, the skill establishes:

- the repository, feature branch, intended base, and current head;
- the applicable repository instructions and pull-request template;
- the current change brief and confirmed intent;
- the complete changeset and relevant submodule or dependent-repository revisions;
- available verification evidence; and
- existing pull-request state and unrelated workspace changes that must be preserved.

The skill stops when the target is ambiguous, the branch is unsuitable, the proposed pull request is not cohesive, or required shared-state authorization is absent. It never pushes directly to `main`.

## Draft-Creation Mode

The author uses draft mode after implementing a coherent first version and gathering proportionate verification evidence. The skill publishes the feature branch when authorized, creates a draft pull request, and produces the initial description from the current change context and observed changeset.

The draft must accurately distinguish:

- developer-confirmed intent, acceptance criteria, constraints, and non-goals;
- delivered implementation facts;
- verification actually performed and known gaps;
- preliminary risk or impact observations; and
- known limitations or unresolved decisions.

Unknown reviewer-derived fields may be labeled as preliminary or pending review. The author must not invent risk validation, independent assurance, or test results to make the draft appear complete.

## Repository-Template Compatibility

An existing repository or organization pull-request template takes precedence as the presentation format. The skill maps the required workflow information into that structure, preserves required policy sections and human-written content, and adds missing context conservatively.

When no applicable template exists, the skill uses a concise default asset with depth proportional to the change. It must not impose a large boilerplate body on a trivial pull request or erase useful project-specific conventions.

## Finalization Mode

The reviewer uses finalization mode only after it has issued a **ready candidate** recommendation for the current head and the developer has explicitly authorized finalization. The skill revalidates the head, reconciles the description with the reviewed changeset, and marks the pull request ready.

Finalization incorporates the reviewer's independent conclusions about delivered behavior, risk, blast radius, verification gaps, limitations, deferred findings, and useful human-review focus. It does not copy the private review transcript into GitHub.

If the head changed materially after the readiness recommendation, the skill returns to review rather than finalizing stale conclusions.

## Intent Protection

The reviewer may clarify presentation but must not semantically change developer-owned intent, acceptance criteria, constraints, or non-goals. If code and intent conflict, finalization stops for developer resolution.

The reviewer may update derived or factual sections to reflect the reviewed code, including implementation summary, verification assessment, risk, limitations, and review guidance. Section authority and lifecycle semantics are owned by [`50-pull-request-lifecycle.md`](./50-pull-request-lifecycle.md).

## Outputs

Draft mode produces:

- a draft pull-request URL and current head identity;
- the structured initial description;
- disclosed verification gaps and unresolved decisions; and
- a concise handoff suitable for the reviewer.

Finalization mode produces:

- a description reconciled to the reviewed head;
- a record of material limitations and accepted deferred work;
- a ready-for-review pull-request state; and
- confirmation of what shared state changed.

Partial failures are reported precisely. The skill verifies existing state before retrying so it does not create duplicate pull requests or overwrite newer human edits.

## Skill Packaging Boundary

The main skill instructions should own mode selection, authorization checks, source reconciliation, template selection, and validation. Shallow resources may contain:

- the proportional default pull-request template;
- guidance for preserving existing repository templates;
- GitHub mutation and recovery procedures; and
- trigger and output evaluation cases.

The package must not contain the code-review phases or finding-resolution workflow. It consumes their durable outputs and links to their contracts rather than restating them.

## External-Action Boundaries

Creating or updating a pull request, pushing a branch, and marking a pull request ready are explicit shared-state actions. The skill performs only the action requested for the current mode and reports it afterward.

The skill never approves, merges, enables automatic merge, bypasses checks, force-pushes protected history, resolves review threads, creates issues, or begins another feature. Merge remains a developer action in the GitHub web interface.
