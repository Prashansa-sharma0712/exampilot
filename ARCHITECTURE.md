# ExamPilot architecture

FastAPI owns ingestion, retrieval, evidence validation and SQLite study state. React/TypeScript displays claims alongside their original evidence. All data stays local by default.

## Pipeline

Source files -> page/slide/section records -> paragraph-aware chunks -> BM25 and semantic vectors -> reciprocal rank fusion -> query-part reranking -> relevant neighbors -> evidence gate -> cited claims -> persistent study state.

Metadata travels with immutable chunk IDs so ranking never loses the original location. Citations reference stored records, not model-generated filenames. Preview endpoints resolve indexed assets inside the configured corpus root.

Embeddings help paraphrases but can retrieve related passages that do not answer a question. BM25 preserves exact terminology. Reciprocal rank fusion combines ranks without pretending the scores are calibrated confidence. Reranking and per-part sufficiency are separate: relevance alone does not establish an answer.

Compound questions retrieve each part independently and combine complementary documents. Duplicate excerpts are suppressed. Adjacent pages may add context but must independently pass the evidence gate. Missing parts stay visibly missing; generation cannot override the gate.

The default provider is conservative extractive answering, with exact evidence quotations and explicit limitations. A configured OpenAI-compatible provider can produce structured evidence judgments and grounded reformulations; citation and quoted-support validation remain server-side. Local sentence-transformer embeddings are the semantic option; BM25-only degraded mode is labeled when embeddings are unavailable.

PDFs preserve pages; PPTX preserves slides and tables; Markdown preserves heading paths. Legacy PPT requires conversion via installed PowerPoint or LibreOffice, retaining the original filename and slide numbering. Handwriting retains the original photograph, OCR/transcription provenance and categorical extraction quality. Unreadable material produces LOW_QUALITY_SOURCE rather than invented words.

SQLite stores sessions, messages, topics, saved claims and quiz attempts. Follow-ups resolve their subject from structured context but run fresh retrieval. Quiz attempts determine weak/strong topics; self-reported study activity is not proof of mastery. Exam Sprint orders weak topics by incorrect attempts and recent activity, without fake course-coverage percentages.

## Evaluation and privacy

Real corpus and all derived outputs stay under ignored paths. Official evaluation requires human-verified locations and exactly 10 single-document, 10 multi-document and 10 near-miss unsupported questions. Synthetic smoke results are separate. A corpus checker counts physical pages/slides and reports manual requirements honestly; file extensions alone cannot verify handwriting difficulty, subject coherence or redistribution rights.

## Tradeoffs

Local single-user application, not a hosted multi-tenant service. Extractive fallback is deliberately limited for paraphrases and complex pedagogy. OCR errors and semantic entailment need human review. Automated citation checks establish location and excerpt validity, not infallible factual entailment. Course coverage is evidence availability, not calibrated confidence.
