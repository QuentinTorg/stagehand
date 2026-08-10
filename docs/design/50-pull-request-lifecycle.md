# Pull-Request Lifecycle

## Workflow Contract Overview

The GitHub pull request is the durable team-facing record for one cohesive change. It begins as a draft while the private author-reviewer loop is active, becomes ready only after independent review and developer authorization, and remains subject to ordinary human review, CI, and repository policy.

This lifecycle is a workflow contract implemented by the narrow [`preparing-pull-requests`](./55-preparing-pull-requests.md) skill. The author uses its draft mode and the reviewer uses its finalization mode after authorization. The workflow never executes the merge.

## Lifecycle States

1. **Local change:** the author works from the confirmed change context on a feature branch.
2. **Draft pull request:** the branch and current intent are recoverable on GitHub, but the change is not yet offered for final team review.
3. **Private review loop:** the author and reviewer iterate through selected findings while the pull request remains draft.
4. **Ready candidate:** the reviewer has completed a full review and recommends readiness.
5. **Ready for review:** the developer authorizes finalization, and the reviewer updates the record and changes its state.
6. **Team review and CI:** humans and repository policy determine whether the pull request may merge.
7. **Merged or closed:** the developer decides the terminal state through GitHub.

A state describes communication readiness, not proof of correctness. Draft status does not excuse poor branch hygiene, and ready status does not imply approval or merge authorization.

## Draft Pull-Request Creation

After an explicit developer request, the author uses the pull-request preparation skill to create the draft after implementing a coherent first version and gathering enough verification to support useful independent review. Creating it earlier is appropriate when remote CI, cross-repository links, or recoverability are needed, provided incomplete claims are labeled clearly.

The draft must identify the intended base and head, represent only the cohesive change, and preserve unrelated work outside the branch. Intermediate commits may be iterative because the expected integration strategy is a squash merge.

For changes involving submodules or coordinated repositories, the draft records the exact revisions and links required to understand which code is under review. A parent-repository pointer change is not a substitute for reviewing the referenced repository changes.

## Durable Pull-Request Description

The description promotes the stable parts of the [change context](./10-change-context.md) into a record usable by agents and teammates. Its depth is proportional to the change, but it should cover:

- the problem and intended outcome;
- the delivered behavior and important implementation boundaries;
- acceptance criteria or observable success conditions;
- explicit non-goals and scope exclusions;
- risk, blast radius, compatibility, and deployment considerations;
- verification performed, results, and material gaps;
- known limitations and developer-approved deferred work; and
- focused guidance about what human reviewers should examine closely.

The description reports the current truth rather than preserving obsolete plans or narrating every private iteration. Linked issues and design documents may own deeper requirements, but the pull request must remain understandable without access to an agent transcript.

## Description Authority and Two-Stage Enrichment

The author creates a useful initial handoff, and the reviewer later enriches it with independent analysis. Ownership follows the meaning of each section:

| Information | Draft responsibility | Finalization authority |
| --- | --- | --- |
| Intent, acceptance criteria, constraints, and non-goals | Author captures developer-confirmed context | Developer-owned; reviewer cannot change semantics |
| Delivered behavior and implementation boundaries | Author records observed facts | Reviewer reconciles with the final reviewed diff |
| Verification | Author records commands, results, and gaps | Reviewer validates evidence and adds material gaps |
| Risk, blast radius, compatibility, and deployment impact | Author may provide preliminary observations | Reviewer supplies the independent final assessment |
| Limitations and deferred work | Author records known items | Developer controls disposition; reviewer records the result |
| Human-review guidance | Author may suggest focus areas | Reviewer supplies final high-value guidance |

If implementation and intent disagree, the reviewer stops for developer resolution rather than editing intent to match the code. Reviewer finalization may improve clarity, but it cannot convert inferred purpose into an authoritative requirement.

## Updates During Private Review

Hunk is the normal scratch surface for private findings, so each review-and-fix exchange need not create GitHub timeline noise. The description is updated during the draft phase when intent, delivered behavior, risk, verification, or limitations materially change. It need not record every intermediate finding or implementation attempt.

If the branch diverges from the stated intent, the developer resolves the discrepancy before review continues. Editing the description cannot silently authorize a scope change; authority remains with the developer under [`10-change-context.md`](./10-change-context.md).

## Readiness Recommendation

The reviewer may recommend **ready candidate** only after reviewing the complete current base-to-head changeset under [`30-reviewing-code.md`](./30-reviewing-code.md). The recommendation includes:

- the reviewed head identity;
- remaining risk and assumptions;
- verification evidence and gaps;
- the disposition of material findings;
- accepted limitations and follow-up candidates; and
- suggested focus areas for human review.

The developer evaluates that recommendation and either authorizes finalization, requests another iteration, changes finding disposition, or revises the change scope. Silence and a passing CI run are not authorization.

## Human-Authorized Finalization

After explicit authorization, the reviewer uses the pull-request preparation skill to finalize the pull request because it has the most current independent understanding of the delivered changeset. Finalization consists of reconciling reviewer-owned and factual sections with the reviewed code, preserving developer-owned intent, and changing the pull request from draft to ready for review.

The reviewer verifies that the head has not materially changed since its recommendation. If it has, the reviewer refreshes the review before finalizing. Finalization does not include self-approval, merge execution, or claims that unperformed tests passed.

When reviewing another developer's pull request, the reviewer does not take ownership of its description or readiness state unless that developer explicitly delegates those actions.

## Team Review, CI, and Later Changes

Once ready, the pull request follows normal repository practices. Human reviewers, required checks, branch protections, and organization policy remain authoritative. This local workflow supplements those controls and cannot weaken or bypass them.

Substantive changes made after readiness return to the author-reviewer loop for proportionate resolution and a complete rereview. Whether the pull request returns to draft depends on the change and repository practice; the workflow must not misrepresent a materially changing branch as stable for reviewers.

Human review feedback may enter the same selected-finding resolution contract in [`40-resolving-findings.md`](./40-resolving-findings.md). GitHub thread replies and resolution remain explicit external actions rather than automatic side effects of editing code.

## Merge Boundary

The developer merges through the GitHub web interface only after applicable human reviews, CI, and repository policies are satisfied. Squash merge is the expected strategy, producing one concise mainline commit per pull request while allowing iterative branch commits.

Agents do not merge, enable automatic merge, bypass checks, force-push protected history, or decide that policy exceptions are acceptable. Branch deletion and post-merge cleanup are also human or repository-controlled actions outside the core workflow.

## Recovery and Failure Handling

The pull request is the recovery anchor after publication. A replacement author or reviewer reconciles its description, current head, checks, and discussion with the repository before proceeding. Agent conversation history may help explain decisions but cannot override the current durable record.

If GitHub is unavailable, local work and private review may continue only while changeset identity and intent remain recoverable. Readiness publication, team review, and merge wait for the durable collaboration boundary to return.
