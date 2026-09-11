# Explicit Project Delegation

The same Stagehand coordinator may deliver an agreed project through its workers. This is broader responsibility, not another agent, worker role, or permission profile. Ordinary workstream management remains the default.

## Establish the assignment

Use the human's explicit instructions to establish the outcome and authoritative requirements, repositories and target branches, delegated decisions, concurrency/resource limits, and stopping conditions. Confirm only missing consequential choices; do not turn a clear startup request into another approval ceremony. Distinguish assigning an outcome from granting decision authority. Do not infer additional authority merely from a large project request; clarify ambiguous grants before exercising them, while continuing work already authorized.

- **Task selection and plan approval:** When granted, decompose and sequence necessary work, approve worker plans within the agreed intent, and continue between workstreams without per-task human approval. Finding disposition is a separate decision to delegate; preserve material in-scope fixes and independent rereview.
- **Publication and integration:** Finalization, external-review publication, and merging are separate grants. Merge authority must identify repositories, target branches, strategy, and required evidence. Only the coordinator exercises delegated merge authority, through GitHub PRs after current-head independent review and required verification/policies; never grant it implicitly to workers. Check the actual base/head before merging and record the result.
- **Limits:** Stay within the granted concurrency and resource budget. Preserve human-only decisions and stop at the agreed outcome, budget boundary, revoked authority, consequential ambiguity, or repeated non-progress. Do not invent optional follow-on projects.

Delegation does not waive repository instructions, sandbox permissions, protected-branch policy, independent review, recoverability, or workspace ownership. Product edits still belong to authors. If another instruction or role skill prevents the requested delegation, surface that conflict rather than hiding it in a worker prompt.

## Direct and recover the work

Keep one concise project note in the private control state, linked from its task records. Preserve the human grant/source, requirements and non-goals, limits, integration targets, significant decisions, remaining work, and acceptance evidence. Reuse an existing project note; no new schema or event ledger is required. On recovery, load it before scheduling and reconcile it with current human direction and actual artifacts. Grants apply only to their named project and may be narrowed or revoked; ambiguous authority is not renewed by a saved summary.

Give workers only their bounded assignment, relevant human-granted authority, and actual approval path. Use the author prompt's delegated-planning modifier when applicable. Do not send the whole project note or this reference. A coordinator-approved plan within delegation needs no duplicate approval in the human's pane.

Own dependency order and integrated acceptance, not just task throughput. Maintain a usable integrated result where practical, verify real consumers and cross-component behavior, and judge completion against the agreed outcome—not the count of finished tasks or PRs. Reuse existing task records, wakes, and the board; a completed workstream is not proof that the project is complete.
