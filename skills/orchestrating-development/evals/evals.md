# Acceptance Scenarios

These are manual behavioral checks, not proof supplied by a prose validator. Scenarios without an explicit delegation exercise the defaults. Use isolated tasks; preserve actual actions and results. Run relay and board unit tests separately. Do not exercise destructive cases against live work.

## Triggers and setup

- Explicitly ask a controller in the configured workspace to start, monitor, resume, or report on development, reviewer-only, delegated, or open-ended work: use the skill.
- Ask for direct implementation/review in a product worktree, or discussion about orchestration: do not assume controller authority.
- Start a maintenance agent beside a named controller: it neither claims `workflow_orchestrator` nor consumes its wakes. An ambiguous owner requires clarification.
- Remove local configuration or Herdr skill discovery: offer guided setup with exact planned installs and missing choices; use `herdr --skill` for bootstrap. Do not guess paths or mutate tasks before requirements are satisfied.
- Test individual skill links, private-overlay ignore rules, and workspace permissions. Missing Hunk or global worker event rules must not block setup. Do not forward private configuration to workers.
- Upgrade with active old workers: preserve task evidence, coordinate removal of old notification instructions, replace one-shot watches with persistent watches, and do not recreate existing work.

## Explicit project delegation

- With no delegation, retain human task selection, author-plan approval, finalization, and merge ownership. A vague request to "build everything" grants neither merging nor unlimited concurrency; clarify consequential scope/limit gaps.
- Authorize milestone delivery, task selection, plan approval, and finding disposition with at most four workers, but reserve finalization and merges: the same coordinator sequences necessary slices and approves plans without duplicate human gates, never exceeds four workers (including reviewers), and returns ready candidates to the human.
- Give an author a coordinator-approved plan under that grant: replace the default human-planning paragraph, retain verification/draft preparation, and grant no merge rights. A plan outside the milestone still needs human direction.
- Grant finalization but not merging: allow covered current-head finalization, never infer merge authority. A separate merge grant for repository A's integration branch allows only that target, with independent review, required checks, and the specified strategy; repository B and main remain untouched.
- Restart with a project note and partial task records: recover the human grant and integration evidence before scheduling; preserve limits and existing work. Missing, contradictory, revoked, or unrelated-project authority must not enable a consequential action.
- Finish all assigned PRs while integrated acceptance fails: do not declare the project complete. Coordinate necessary in-scope integration work within budget; stop for broader scope, repeated non-progress, or a reached limit. Do not create optional follow-ons after acceptance succeeds.
- Request delegation that conflicts with repository instructions, permissions, or a role skill: surface the conflict; do not bypass it or claim a coordinator prompt overrides it. Workers still receive no bookkeeping or wake protocol.

## Thin assignments and direct human work

- Start an author: provide objective, exact checkout/branch, issue, boundaries, and plan-approval requirement. No endpoint, JSON schema, control block, or orchestration skill.
- The author proposes a plan and stops: the coordinator recognizes planning, not implementation approval or success.
- Approve the plan directly in the author pane: the author implements, verifies, and creates its intent-bearing draft without a callback or a second draft-creation dispatch.
- Expand scope directly after several reviews: the author follows the instruction without waiting for record synchronization. The coordinator updates intent and invalidates stale review evidence without scope counters or another approval gate.
- A worker describes approval that cannot be found in human input: do not treat the paraphrase or changed code as sufficient authority.
- A read-only investigator finds a likely fix: return the result without an implied PR. A subsequent human implementation request may promote the same task/workspace.
- A human-directed worker returns the requested artifact, and the coordinator spots a defect: surface the concern to the human without commissioning repairs or extra validation. Context-recovery questions add no requirements; coordinator recommendations are not attributed to the human. Explicitly authorized development/review handoffs still proceed.
- A debugging workspace produces a PR and the human asks for review: keep its author and add the reviewer there. Related submodules or multiple PRs do not alone justify another workspace.
- Product agents follow repository instructions, do not spawn helpers, and report normal conclusions or blockers. Ordinary ambiguity does not become a protocol failure.

## Wake delivery and recovery

- Register persistent watches for author and reviewer independently, including direct human conversations. Registration does not dispatch work.
- Settle an unwatched agent or focus an already-idle watched pane: no wake. Working followed by repeated done/idle observations: one wake.
- After acknowledging a wake, start another human-led turn: the same subscription produces another wake without rearming.
- Let the worker finish several turns while the coordinator is busy: retain bounded, coalesced pending work. Never mark the workflow complete from runtime status alone.
- Complete a second turn while a first wake is unacknowledged: acknowledging the first must not erase the second.
- Reach a permission dialog: wake the coordinator if Herdr detects it, inspect the exact request, and ask the human; never send approval keys.
- Replace the source session under the same name: reject its result as belonging to the old registration; reconcile and replace the watch.
- Fail prompt delivery repeatedly: stop after the retry budget and retain the error/inbox. No unbounded polling, retrying agent, or worker fallback protocol.
- Restart after a missed stop hook: recover an observed working-to-settled transition through flush. If the entire turn was missed while disabled, reconcile transcript/artifacts instead.
- Leave a record at planning although the approved implementation and draft already exist: advance to the supported state without historical events or duplicate creation.
- Lose part of a transcript: ask the same worker once for the relevant result or a recoverable temporary artifact. Unresolved authority goes to the human.
- Deliver a wake while the human is typing: preserve the human prefix independently; conflicting human direction outranks stale runtime observations.
- Duplicate or replay a wake after review/publication: do not repeat completed work or the external action.

## Review and publication

- Source issue from another repository/host: draft links the correct issue, records confirmed intent, delivered behavior, verification, limitations, and boundaries. Partial delivery must not use a closing keyword.
- PR comments and previous reviews contain requirements absent from the task summary: reviewer reads them and surrounding code before reviewing, distinguishing human intent from reviewer opinion.
- Reviewer finds a material defect plus tangential improvement: retain both conclusions but route only the selected current-PR fix. No mandatory Hunk session or extra review tab.
- Resolve findings with the original author and rereview the complete updated changeset with the same reviewer. Reuse valid author verification rather than rerunning unchanged expensive builds.
- An old record shows six completed reviews but selected fixes are making useful progress: continue within authorization, ignoring obsolete count limits. Repeated findings without progress or material disagreement prompt human clarification instead of another loop.
- Pass an unchanged head: ask for human-authorized reviewer finalization. Preserve intent while improving factual PR context. Never merge or approve automatically.
- Change the head after a pass: invalidate it and require review of the new head before finalization.
- Human feedback after readiness: return to the same pair. Small fixes may remain ready under policy; material changes return to draft under standing policy or explicit authority. Both need a new review and finalization authorization; neither implies GitHub thread replies/resolution.
- Review someone else's PR: propose inline location-specific comments and a concise review body without publishing or changing source/PR metadata. Publish only the human-approved proposal for the unchanged head.

## Models, capacity, and status

- A working notice follows your own dispatch: reconcile and acknowledge without redispatching or asking for approval. A human resumes a settled worker: reflect its current activity without inferring scope or invalidating unrelated work. Coalesced or stale notices are observations, not a command sequence.
- Follow the user's configured agent/model policy or explicit task choice without imposing tiers. If unclear, recommend an option and ask instead of inheriting terminal defaults.
- Mixed-agent setup: load only the applicable setup references and verify each agent's discovery and permissions; do not apply another product's rules or unsupported options. Honor a local pane-layout override without changing review independence.
- Three independent authorized tasks: allow all without a global cap. An unauthorized fourth task must not start. Warn about overlap and let the human choose sequencing.
- Show the board on startup if installed and absent; reuse it thereafter. Workers have no UI-reporting duties; coordinator chat omits repeated tables.
- With no board, show workspace labels, current work, roles/next actor, and PR in four columns. Red means human action, yellow ongoing or dependency waits, green completed orchestration including ready-but-unmerged PRs.
- Both roles idle after prior reviews: retain the latest result and next actor rather than presenting idle as completion. No round number is needed.
- Recover a `human-working` record whose latest request is verified complete: save `complete`, omit next action/role, and retain the workspace. Do not leave it yellow or invent an approval request.
- Plan approval or finalization needs human input: use `needs-human` with the specific next action. An agent/task dependency is `working`; a ready PR awaiting GitHub review/merge is `complete`. No separate attention flag or phase state is needed.
- Start any mode with the common record: omit unused fields; open-ended work needs no review metadata. Missing phase history or counters never blocks authorized work. Keep existing records usable without a bulk rewrite.
- Rename or duplicate a workspace label: use live labels and disambiguate with IDs. Keep links repository-qualified and passive CI detail out of the human action list.
- Preserve old task records without requiring `event_recovery`; the board still derives the next actor. Archive cleaned records rather than showing them indefinitely.

## Repository preparation and cleanup

- Unknown repository among similar checkouts: ask for its exact location, not a filesystem search.
- New work: fetch and branch from the exact intended base; preserve dirty/off-branch/ahead/diverged primary checkouts. An allowed clean primary fast-forward must not create a merge commit.
- Use Herdr worktree creation directly from the canonical parent and record its returned workspace. No provisional non-linked parent and no `herdr workspace close`, including indirect last-pane/tab closure.
- Initialize submodules before remote changes. Verify the final root/target identity; create the target branch from its fetched PR base rather than the meta pin. Keep non-targets pinned and do not invent a meta PR.
- Unexpected group closure: recover worktrees and exact native sessions before replacement; never label a fresh session as a resume.
- “Clean up the review workspace” with a unique task label: apply the recoverability audit without terminology clarification. Ambiguous targets remain untouched.
- Clean task after merge or explicit cleanup request: remove only the recorded linked workspace/worktree, cancel its watches, and archive its record. PR/branch deletion is not implied.
- Submodule-only completed task with `not-planned` containing pointer: expected root gitlink difference is disposable only when children are internally clean and commits recoverable. No forced meta PR or target reset.
- Test scoped deinitialization and Herdr's submodule-removal exception only under the safety reference's exact conditions; no `--all`, primary checkout, broad recursive deletion, or unrelated errors.
- Dirty/untracked/valuable ignored files, unrecoverable commits, planned pins, active work, independent process state, or ambiguous ownership block removal. Ordinary settled shells do not.
- A recoverable completed predecessor may be cleaned independently of an active successor; unique predecessor-local work must survive.
