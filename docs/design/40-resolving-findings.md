# Resolving Findings

## Skill Contract Overview

The finding-resolution skill lets the original author safely modify a changeset to address review findings selected for the current pull request. It revalidates each finding against current code, implements the smallest cohesive correction, gathers focused verification evidence, and returns the complete changeset to the same reviewer for independent rereview.

The skill replaces the current broad feedback-processing workflow with a narrow implementation mode loaded into the author agent's existing session. It does not require a third implementation agent and does not own review analysis, finding publication, issue creation, pull-request communication, or readiness decisions.

## Explicit Trigger

The skill activates only when the developer explicitly asks an agent to modify code in response to review feedback or invokes the skill by name. Feedback may originate from Hunk, GitHub, a review document, or a structured agent handoff.

The original author normally loads the skill in its existing session, preserving design and repository context. The expected human transition is defined in [`05-human-workflow.md`](./05-human-workflow.md); merely returning findings to the session does not activate modification.

Merely displaying, summarizing, discussing, or reviewing feedback does not authorize code changes. If the developer requests that an untriaged set be “addressed,” the skill may validate and propose dispositions, but it must obtain a clear selection before editing.

The skill must not activate in the reviewer agent that produced the findings. Separation between review judgment and implementation protects independent rereview and prevents the reviewer from silently converting every observation into work.

## Inputs and Authorization

The author receives:

- the current changeset identity and intended base;
- the confirmed change brief or pull-request description;
- applicable repository instructions;
- the findings explicitly selected as **fix in this pull request**;
- any developer decisions that resolve ambiguity; and
- existing verification evidence and workspace constraints.

Each selected finding should follow the medium-independent contract in [`30-reviewing-code.md`](./30-reviewing-code.md). Adapter metadata may identify its Hunk annotation, GitHub thread, or source document, but transport-specific fields do not change the meaning of the finding.

Selection authorizes investigation and an appropriately bounded fix. The author's retained design conversation may inform implementation, but it cannot override the durable change brief or the selected finding. Selection does not authorize a material change to product intent, architecture, compatibility, public behavior, or pull-request scope. Those discoveries return to the developer for decision.

## Finding Disposition

Review findings have one developer-controlled disposition:

- **Fix in this pull request:** eligible input to the author.
- **Developer decision required:** blocked until intent or scope is clarified.
- **Follow-up candidate:** kept outside the current changeset; issue creation is a separate human decision.
- **No change:** declined, accepted as-is, superseded, or informational.

Reviewer recommendations help the developer decide but do not set disposition. The author receives only the first category for implementation and must not opportunistically implement the others.

## Revalidation Before Editing

The author treats feedback as a technical claim rather than an instruction to apply blindly. For each selected finding, it inspects the current code and relevant contracts to determine whether the finding remains valid, is already resolved, conflicts with another finding, or depends on an incorrect assumption.

The author reports a finding instead of editing when it is stale, unsupported, mutually inconsistent, or cannot be resolved inside the authorized boundary. Revalidation must not become a second broad code review; newly noticed tangential concerns are returned as observations for developer disposition.

Related findings may be implemented as one cohesive fix when separate edits would conflict or duplicate work. The handoff must preserve traceability from each selected finding to its result.

## Resolution Risk and Human Involvement

The finding's resolution-risk classification guides autonomy:

- **Routine:** local, behavior-preserving, and mechanically verifiable within the accepted intent. The author may proceed when the developer selected the finding or granted standing authorization for this class.
- **Judgment required:** admits materially different valid implementations or affects interfaces, architecture, compatibility, deployment, or user-visible behavior. The author presents the decision and waits for direction.
- **Scope changing:** cannot be completed without broadening the cohesive change. The author stops and returns the finding for redisposition or pull-request replanning.

Estimated effort alone does not determine risk. A large mechanical correction may be routine, while a one-line contract change may require developer judgment.

## Implementation and Scope Control

The author implements the smallest maintainable change that resolves the selected finding and remains consistent with the change brief. It preserves repository conventions, documented intent, unrelated workspace state, and the engineering standards in the target repository.

The author must not:

- bundle adjacent cleanup or speculative improvements;
- redesign code beyond what is necessary to resolve the selected finding;
- weaken tests, warnings, validation, or type safety to make a check pass;
- rewrite unrelated author changes;
- begin fixing follow-up candidates; or
- reinterpret reviewer suggestions as mandatory implementation details when a safer equivalent resolution exists.

If a selected fix reveals that the pull request is no longer cohesive, the author pauses rather than concealing scope growth inside the review loop.

## Verification

Verification is proportionate to the changed behavior and the finding's claimed consequence. It should reproduce the defect when practical, demonstrate the corrected behavior, and check important nearby failure paths. The author uses repository-approved builds, tests, static analysis, or containerized checks as applicable.

Focused verification provides fast feedback, but broader checks remain necessary when the fix changes shared interfaces, state, build configuration, or cross-component behavior. A passing command does not prove resolution unless its assertions exercise the relevant contract.

The author records exact commands, outcomes, limitations, and artifacts needed by the reviewer. It does not mark its own changes reviewed.

## Handoff to Rereview

The resolution handoff contains:

- the new changeset identity;
- each selected finding and its status: resolved, already resolved, blocked, or disputed;
- a concise explanation of implemented changes;
- verification evidence and known gaps;
- any developer decisions made during resolution; and
- observations returned for disposition without being implemented.

The complete updated changeset then returns to the same reviewer's rereview contract in [`30-reviewing-code.md`](./30-reviewing-code.md). Resolution is not complete merely because every prior annotation has a reply or a changed line.

## Skill Packaging Boundary

The eventual skill should keep its core instructions focused on explicit triggering, finding revalidation, authorization checks, bounded implementation, verification, and rereview handoff. Detailed risk guidance and the handoff template may use shallow references loaded only when applicable.

Hunk and GitHub ingestion belong to the adapters in [`60-review-adapters.md`](./60-review-adapters.md). The skill consumes a normalized selected-finding set and must not require a particular review medium.

## External Actions and Boundaries

Code resolution does not implicitly authorize the author to:

- create or close GitHub issues;
- reply to, resolve, or publish review threads;
- create commits, push branches, or force-update history;
- alter the pull-request description or readiness state;
- approve or merge the pull request; or
- skip the complete independent rereview.

Any such action requires a separate explicit request and follows the [pull-request lifecycle](./50-pull-request-lifecycle.md) or [review-adapter](./60-review-adapters.md) contract. This separation prevents local repair from causing unrequested external state changes.
