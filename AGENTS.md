# ExamPilot engineering rules

- The course material is the source of truth. Never supply unsupported course facts.
- Preserve file, page, slide, section, original asset and extraction quality through the pipeline.
- Attach validated citations to individual claims. Conversation history is context, never evidence.
- Report measured evaluations only; distinguish synthetic tests, draft labels and human-verified ground truth.
- Keep architecture simple and explainable; test meaningful behavior and never weaken tests to pass.
- Commit and push genuine tested milestones incrementally. Do not rewrite history.
- Never commit secrets, `.env`, `corpus/private`, or derived private extracts, previews, indexes or evaluation content.
- Real ingestion and corpus checking default to `corpus/private`; `corpus/demo` is explicitly synthetic.
- Keep private derived data in ignored `data/`. Do not send private material to external providers unless explicitly configured by the user.
- Preserve useful user work and source originals. Bind development servers to localhost.
