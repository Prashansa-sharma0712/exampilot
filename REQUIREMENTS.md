# Submission acceptance map

Status legend: DONE, PARTIAL, REQUIRES_REAL_CORPUS, REQUIRES_HUMAN_VERIFICATION, REQUIRES_EXTERNAL_CREDENTIAL.

| Requirement | Verified current status | Evidence / completion gate |
|---|---|---|
| Real corpus: 60+ pages/slides | DONE | 695 PDF pages + 63 slides + one image = 759 physical units |
| Four formats: PDF, slides, text, handwriting | REQUIRES_REAL_CORPUS | Text directory currently empty |
| Two handwritten pages; one difficult | REQUIRES_REAL_CORPUS | Only one image currently present |
| Diagram/table/equation source | REQUIRES_HUMAN_VERIFICATION | Inspect originals |
| Safe private corpus handling | DONE | Git ignore plus private derived-data policy |
| Remove access-test file | DONE | Initial cleanup |
| PDF/PPTX/Markdown/text/image ingestion | DONE | Format extraction and metadata tests; real corpus ingested |
| Legacy PPT ingestion | DONE | Apache POI extracted and rendered all 63 slides locally |
| Handwriting extraction, quality, original preview | PARTIAL | Test real image and fallback |
| Structure-aware chunks and stable citations | DONE | Tested page/slide/section preservation and stable IDs |
| Semantic + BM25 hybrid, rerank, filters, neighbors | DONE | Local 384-dimensional model; RRF, lexical reranking and relevant neighbors implemented |
| Multi-document decomposition and synthesis | PARTIAL | Require complementary evidence |
| ANSWERED/PARTIALLY_ANSWERED/NOT_COVERED/LOW_QUALITY_SOURCE/ERROR | DONE | Explicit Pydantic states and deterministic tests |
| Evidence sufficiency, refusal, claim validation | PARTIAL | Near-miss and invalid-citation tests |
| Original source inspection | PARTIAL | Evidence viewer |
| Conversation and fresh follow-up retrieval | DONE | SQLite sessions and reference resolution; API integration tests |
| Explain simply, compare, 5-mark, quiz | PARTIAL | Grounded actions |
| Quiz grading, weak topics, saved revision | DONE | Cloze grading, idempotent attempts, weak-topic updates and saved evidence tested |
| Exam Sprint dashboard | PARTIAL | Reflect real session state |
| React/Vite/TypeScript/Tailwind frontend | PARTIAL | Lint and production build pass; browser checks pending |
| FastAPI/Pydantic/SQLite backend | DONE | 17-test resumption baseline passes; localhost health endpoint verified |
| Provider abstraction and safe errors | PARTIAL | Real provider adapter; mocks only in unit tests |
| Corpus checker defaults to private | DONE | Real counts measured; exits 1 for missing text and second handwritten image |
| 10 single + 10 multi answerable with locations | REQUIRES_HUMAN_VERIFICATION | Draft from actual corpus, never fake approval |
| 10 plausible absent questions | REQUIRES_HUMAN_VERIFICATION | Search whole corpus and review |
| Reproducible evaluation and failure logs | DONE | Synthetic run produced JSON results and failures; official human-verification gate implemented |
| Honest measured metrics | DONE | No official results claimed before verified dataset |
| README run/fallback/limitations and architecture | PARTIAL | Final tested commands |
| Incremental tested commits and pushes | PARTIAL | Real milestones |
| Public GitHub visibility | REQUIRES_HUMAN_VERIFICATION | Inspect repository visibility |
| Two-minute working video and Drive link | REQUIRES_HUMAN_VERIFICATION | Script; human recording/upload |
| Final secret scan, tests, clean Git | PARTIAL | Final quality gate |
