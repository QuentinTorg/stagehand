# Agent Selection

Choose from a small, locally configured set and set model and reasoning effort explicitly at launch. Never inherit the terminal's last-used choice.

- **Economical:** exploration, known-pattern implementation, focused tests, and small reviews with clear acceptance criteria.
- **Stronger:** unresolved architecture, cross-component semantics, ambiguous diagnosis, subtle concurrency/ownership/security, or risks focused tests cannot expose.
- **Beyond the configured range:** ask the human with the unresolved problem and a bounded proposed assignment.

Choose reviewer capability from the change's reasoning difficulty and risk, not the author's model or raw line count. Several files or unfamiliar tooling alone do not require promotion.

After two substantive attempts fail to advance the same problem, distinguish missing context or environment trouble from reasoning difficulty. Clarify, narrow, or promote rather than repeat. Preserve the session when the installed agent supports a safe model change or exact-session resume; otherwise explain replacement. Never change permission settings to promote a model.

Record a brief selection reason in task state, not a worker protocol. Do not create an extra planning agent for routine choices.

For Codex, [OpenAI's GPT-5.6 guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6) describes Luna as efficient and Sol as flagship-capability, with medium reasoning as a balanced starting point. A two-choice Luna/Sol policy is a Stagehand starting recommendation, not a measured quality or cost guarantee. Set exact choices in local configuration and adjust from actual accepted results; stronger reasoning should earn its cost.
