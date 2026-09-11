# Agent Selection

Choose the agent and model from a small, locally configured set. Set supported options, such as reasoning effort, explicitly rather than inheriting unintended terminal defaults. Author and reviewer may use different agent products.

- **Economical:** exploration, known-pattern implementation, focused tests, and small reviews with clear acceptance criteria.
- **Stronger:** unresolved architecture, cross-component semantics, ambiguous diagnosis, subtle concurrency/ownership/security, or risks focused tests cannot expose.
- **Beyond the configured range:** ask the human with the unresolved problem and a bounded proposed assignment.

Choose reviewer capability from the change's reasoning difficulty and risk, not the author's model or raw line count. Several files or unfamiliar tooling alone do not require promotion.

After two substantive attempts fail to advance the same problem, distinguish missing context or environment trouble from reasoning difficulty. Clarify, narrow, or promote rather than repeat. Preserve the session when the installed agent supports a safe model change or exact-session resume; otherwise explain replacement. Never change permission settings to promote a model.

Record a brief selection reason in task state, not a worker protocol. Do not create an extra planning agent for routine choices.

Keep exact agents, models, and supported options in local configuration. Adjust choices from accepted results; stronger reasoning should earn its cost.
