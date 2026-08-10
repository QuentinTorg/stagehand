# Review Adapters

## Integration Contract Overview

Review adapters carry the same review result between the reviewer, developer, author, and an external surface. They preserve finding meaning, changeset identity, and authorization state without deciding whether a finding is valid, whether it belongs in the pull request, or how it should be fixed.

Hunk is the default adapter for private review of the developer's agent-authored changes. GitHub is the team-facing adapter for reviewing another developer's pull request and for the pull-request mutations performed through [`55-preparing-pull-requests.md`](./55-preparing-pull-requests.md). Neither surface is the source of product intent.

## Common Review Contract

Adapters consume the review summary and findings defined by [`30-reviewing-code.md`](./30-reviewing-code.md). They must preserve:

- the reviewed base and head or equivalent working-tree identity;
- stable finding identifiers;
- file and line or hunk locations when applicable;
- observation, consequence, evidence, and uncertainty;
- severity, current-change relevance, and resolution risk;
- the review recommendation; and
- whether content is a reviewer recommendation or a developer-approved disposition.

Presentation may vary by medium, but an adapter must not strengthen tentative language, convert a follow-up candidate into required work, or imply that publication authorizes implementation.

## Hunk Adapter

For the private loop, the reviewer connects to the Hunk session associated with the author's checkout or worktree, verifies that it displays the intended changeset, and places concise findings beside the relevant diff. A review summary carries changeset-level risk, verification gaps, and findings that lack a stable inline location.

The developer uses the visible diff and findings to decide disposition. Only findings selected as **fix in this pull request** are handed back to the author under [`40-resolving-findings.md`](./40-resolving-findings.md). Developer notes and reviewer findings must remain distinguishable so an agent cannot mistake a displayed observation for authorization.

The author may consume selected findings from the live Hunk session while retaining its original design context. After edits, Hunk reloads or refreshes the changeset for the same reviewer. Inline locations are treated as anchors into a particular diff, not durable identities after code moves.

Live Hunk state improves interaction but is not assumed to be permanent. When recovery across session loss matters, the normalized review or selected-finding handoff may be saved as a local sidecar outside committed product files and tied to the reviewed head. Hunk's agent-context presentation may render such a snapshot, but it does not become the authoritative change brief.

The adapter does not require every analytical check to appear as a comment. It transports actionable findings and useful summary context, not the reviewer's internal audit log.

The initial implementation should reuse Hunk's existing review skill for live-session discovery, navigation, reload, and comment operations. The reviewing-code and finding-resolution skills retain judgment and authorization rules rather than duplicating Hunk command guidance.

## GitHub Adapter

For another developer's pull request, the reviewer prepares a normal GitHub review from the same medium-independent result. Findings with stable diff locations become inline comments; changeset-level concerns and the overall recommendation belong in the review summary.

Before publication, the reviewer confirms the current pull-request head and presents the exact proposed review to the developer. Publication requires explicit authorization. The GitHub review event should accurately represent the conclusion and repository norms without overstating certainty.

The adapter avoids duplicating private Hunk iterations onto the developer's own pull request. That pull request receives the finalized description and ready transition defined in [`50-pull-request-lifecycle.md`](./50-pull-request-lifecycle.md) through the preparation skill, not a transcript of local repair.

GitHub comments from human reviewers may be normalized into the finding contract for the author, but fetching feedback does not select it for implementation. Replies, thread resolution, issue creation, approval, and readiness changes remain separately authorized external actions.

## Publication and Mutation Boundaries

Reading a review surface and drafting output are reversible local actions. Publishing comments, changing pull-request state, resolving threads, and creating issues affect shared state and require developer authorization unless a narrowly scoped standing authorization exists.

Authorization applies to the presented content and current changeset. If either changes materially before publication, the adapter refreshes the draft and obtains renewed authorization. It must not silently add newly discovered findings to an approved review.

The adapter never merges, rewrites branch history, or changes repository policy.

## State Ownership and Duplication

Each kind of information has one owner:

- the change brief and durable delivered context belong in the pull-request description;
- private findings and dispositions belong in the Hunk-centered review loop or its recovery snapshot;
- published teammate feedback belongs in GitHub review threads;
- selected-finding implementation status belongs in the author-to-reviewer handoff; and
- unresolved future work becomes a GitHub issue only after developer approval.

Adapters may link or summarize these sources but should not maintain competing copies that can drift. A stale copy is labeled with its changeset identity rather than silently reconciled by guesswork.

## Failure and Recovery

Before delivering or publishing, an adapter confirms that its target repository, worktree, pull request, and head match the reviewed changeset. A mismatch stops mutation and returns control to the reviewer for refresh.

If an inline location is no longer valid, the adapter preserves the finding as a file-level or summary-level item instead of dropping it. If publication partially succeeds, it reports exactly what was created and avoids retrying blindly, which could duplicate comments.

If Hunk is unavailable, the reviewer may provide the same normalized findings through a local temporary document or direct agent handoff. If GitHub is unavailable, the review may be prepared locally, but shared publication waits until the current head can be revalidated.

Tool-specific command syntax belongs in adapter implementation references rather than this contract so Hunk and GitHub changes do not destabilize the workflow design.
