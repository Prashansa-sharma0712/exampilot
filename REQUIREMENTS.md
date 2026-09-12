# Submission acceptance map

Status legend: DONE, PARTIAL, REQUIRES_REAL_CORPUS, REQUIRES_HUMAN_VERIFICATION, REQUIRES_EXTERNAL_CREDENTIAL.

| Requirement | Status at inspection | Evidence / completion gate |
|---|---|---|
| Real corpus: 60+ pages/slides | PARTIAL | Count actual PDF and deck pages |
| Four formats: PDF, slides, text, handwriting | REQUIRES_REAL_CORPUS | Text directory currently empty |
| Two handwritten pages; one difficult | REQUIRES_REAL_CORPUS | Only one image currently present |
| Diagram/table/equation source | REQUIRES_HUMAN_VERIFICATION | Inspect originals |
| Safe private corpus handling | DONE | Git ignore plus private derived-data policy |
| Remove access-test file | DONE | Initial cleanup |
| PDF/PPTX/Markdown/text/image ingestion | PARTIAL | Implement and test metadata preservation |
| Legacy PPT ingestion | PARTIAL | Convert locally; verify slide mapping |
| Handwriting extraction, quality, original preview | PARTIAL | Test real image and fallback |
| Structure-aware chunks and stable citations | PARTIAL | Add tests |
| Semantic + BM25 hybrid, rerank, filters, neighbors | PARTIAL | Implement and measure |
| Multi-document decomposition and synthesis | PARTIAL | Require complementary evidence |
| ANSWERED/PARTIALLY_ANSWERED/NOT_COVERED/LOW_QUALITY_SOURCE/ERROR | PARTIAL | Explicit schema and tests |
| Evidence sufficiency, refusal, claim validation | PARTIAL | Near-miss and invalid-citation tests |
| Original source inspection | PARTIAL | Evidence viewer |
| Conversation and fresh follow-up retrieval | PARTIAL | Persist sessions; integration tests |
| Explain simply, compare, 5-mark, quiz | PARTIAL | Grounded actions |
| Quiz grading, weak topics, saved revision | PARTIAL | SQLite state tests |
| Exam Sprint dashboard | PARTIAL | Reflect real session state |
| React/Vite/TypeScript/Tailwind frontend | PARTIAL | Lint/build/browser checks |
| FastAPI/Pydantic/SQLite backend | PARTIAL | Startup and pytest |
| Provider abstraction and safe errors | PARTIAL | Real provider adapter; mocks only in unit tests |
| Corpus checker defaults to private | PARTIAL | Counts plus manual verification flags |
| 10 single + 10 multi answerable with locations | REQUIRES_HUMAN_VERIFICATION | Draft from actual corpus, never fake approval |
| 10 plausible absent questions | REQUIRES_HUMAN_VERIFICATION | Search whole corpus and review |
| Reproducible evaluation and failure logs | PARTIAL | Machine-readable results |
| Honest measured metrics | DONE | No official results claimed before verified dataset |
| README run/fallback/limitations and architecture | PARTIAL | Final tested commands |
| Incremental tested commits and pushes | PARTIAL | Real milestones |
| Public GitHub visibility | REQUIRES_HUMAN_VERIFICATION | Inspect repository visibility |
| Two-minute working video and Drive link | REQUIRES_HUMAN_VERIFICATION | Script; human recording/upload |
| Final secret scan, tests, clean Git | PARTIAL | Final quality gate |
