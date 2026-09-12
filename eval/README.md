# Evaluation without invented certainty

Real labels and outputs live in ignored `data/eval/`; they may reveal private source content. Never commit them. The official runner defaults to `data/eval/questions.json` and refuses unverified labels. Draft diagnostics require the explicit `--allow-draft` option and are marked non-official.

Use exactly 10 single-document, 10 multi-document and 10 plausible unsupported questions. Answerable entries require exact locations, expected keywords and a rationale. Multi-document entries must name two different files. Review against the originals, then set `verification: human_verified`, `verified_by` and `verified_at`. The software checks these attestations; it cannot prove a human actually reviewed them. Do not mark them on the basis of automated inspection.

Source identity is its relative path inside the corpus. PDF pages are physical PDF pages (starting at 1), not printed page labels. Image pages are 1 even when the photographed page has a different printed number. Slide numbers are presentation order. Markdown locations are heading paths.

Commands from repository root:

```powershell
python scripts/validate_eval.py data/eval/questions_draft.json --allow-draft
python eval/run_eval.py --dataset data/eval/questions_draft.json --allow-draft --output data/eval/draft-results.json
python eval/run_eval.py
```

Metrics distinguish single/multi success proxies, precise source-location matches, refusals, citation precision proxies, retrieval recall and handwriting retrieval. Success is a status + keyword + location check; this is not a semantic grader. Review answer correctness and claim entailment separately. Results include timestamps, corpus hashes, dataset hash, provider mode and per-question diagnostics. Failures do not silently update ground truth.

`eval/demo_questions.json` is an authored synthetic regression set. Run it against a separate demo database. It does not count toward the real-course evaluation. No provider mocks are used by the evaluation runner; mocks are confined to unit tests.
