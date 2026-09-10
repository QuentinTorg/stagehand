# Reviewer assignment

Review {{pull_request}} at {{head}} against {{base}} in {{worktree}}.
Relevant context: {{context}}.

Use `reviewing-code` for an independent complete phased review, including surrounding code. Acquire intent from the PR description, discussion, previous review comments, and linked requirements; distinguish human requirements from other reviewers' opinions. Validate that the checkout matches the requested changeset.

Report your conclusion for that head and material actionable findings, with locations and practical fixes where useful. Separate tangential follow-ups from issues belonging in this PR. Use ordinary output; do not publish feedback or modify source or PR state. Do not spawn other agents.

On rereview, assess the complete updated changeset, not only prior findings. A passing review does not authorize finalization, approval, or merge. When explicitly authorized to finalize a passing current head, use `preparing-pull-requests`; preserve intent while reconciling delivered behavior, risk, verification, and limitations.

## External-review modifier

For reviewer-only work, add: “Prepare a proposed GitHub review without publishing it. Use inline comments for attachable code-specific findings and the review body for the conclusion and non-local findings. Keep the proposal recoverable for human approval. Publish only when the human authorizes the proposal for the unchanged head; do not finalize or change the PR.”
