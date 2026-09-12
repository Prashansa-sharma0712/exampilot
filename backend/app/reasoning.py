import re
from time import perf_counter
from .models import Answer, Claim, Need
from .retrieval import tokens, definition_pattern, PREDICATES
from .query import decompose, intent


def normalize(text):
    return re.sub(r'\s+', ' ', text).strip().casefold()


def validate_claims(claims, chunks):
    evidence = {c.chunk_id: c for c in chunks}
    for claim in claims:
        for cid in claim.citations:
            if cid not in evidence:
                raise ValueError('Unknown citation ID')
            source = evidence[cid]
            quote = claim.quotes.get(cid, '')
            if len(quote.strip()) < 12 or normalize(quote) not in normalize(source.text):
                raise ValueError('Citation quote not present in source')
            if source.extraction_quality == 'LOW':
                raise ValueError('Low-quality source cannot support authoritative claim')
    return True


def excerpt_for(need, chunk):
    terms = set(tokens(need))
    if not terms:
        return None
    # Preserve nearby lines for scanned PDF text. All returned text remains verbatim.
    candidates = [p.strip() for p in re.split(r'\n\s*\n|(?<=[.!?])\s+(?=[A-Z])', chunk.text) if p.strip()]
    paragraphs = re.split(r'\n\s*\n', chunk.text)
    for i, heading in enumerate(paragraphs[:-1]):
        if len(heading.split()) <= 8 and terms.issubset(set(tokens(heading))):
            candidates.append(heading + '\n\n' + paragraphs[i + 1])
    if len(candidates) < 2:
        lines = chunk.text.splitlines()
        candidates += ['\n'.join(lines[i:i+6]) for i in range(len(lines))]
    best = None
    pattern = definition_pattern(need)
    require_definition = bool(re.search(r'^(?:what\s+(?:is|are)|define)\b', need, re.I))
    for quote in candidates:
        if not 12 <= len(quote) <= 2000:
            continue
        present = set(tokens(quote))
        # Conservative all-term gate: related terminology alone is insufficient.
        if not terms.issubset(present):
            continue
        if '[illegible]' in quote or '[uncertain]' in quote:
            continue
        if len(present - terms) < 3:
            continue
        # A title/list mentioning the topic is not an explanation.
        if not re.search(r'\b(' + PREDICATES + r'|used|has|have|can|cannot|must|called|does|do|shall|will)\b', quote, re.I):
            continue
        direct = bool(pattern and pattern.search(quote))
        if require_definition and pattern:
            match = pattern.search(quote)
            if match:
                prefix = quote[:match.start()]
                # A conditional specialization is not the requested definition.
                if re.search(r'\b(if|unless|such)\b', prefix, re.I):
                    continue
                # Remove unrelated introductory questions while keeping an exact
                # source substring, then stop at the first complete sentence.
                quote = quote[match.start():]
                end = re.search(r'[.!?](?:\s|$)', quote)
                if end:
                    quote = quote[:end.start()+1]
        if require_definition and not direct:
            continue
        if best is None or (direct, -len(quote)) > (bool(pattern and pattern.search(best)), -len(best)):
            best = quote
    return best


def source_view(c):
    return {**c.model_dump(exclude={'original_asset_path'}), 'location': c.location, 'preview_url': f'/api/source/{c.chunk_id}/preview', 'original_url': f'/api/source/{c.chunk_id}/original'}


def answer_question(question, index, config, document_id=None, source_type=None, action='ask'):
    start = perf_counter()
    needs = decompose(question)
    query_intent = intent(question, action)
    if len(needs)>12:
        return Answer(status='ERROR',answer='This question has more than 12 evidence needs. Split it into smaller questions.',resolved_question=question)
    if action == 'example' and 'example' not in question.lower():
        needs = [n + ' example' for n in needs]
    gathered = {}
    by_need = {}
    for need in needs:
        hits = index.search(need, document_id=document_id, source_type=source_type)
        by_need[need] = hits
        gathered.update({c.chunk_id: c for c in hits})
    chunks = list(gathered.values())
    elapsed = (perf_counter() - start) * 1000
    warnings = [index.warning] if index.warning else []
    claims, coverage = [], []
    try:
        if config.llm_provider == 'openai_compatible' and chunks:
            from .providers import judge_and_answer
            judged = judge_and_answer(question, needs, chunks, config, action)
            claims, coverage = judged.claims, judged.coverage
            validate_claims(claims, chunks)
            cited = {cid for c in claims for cid in c.citations}
            for n in coverage:
                if n.supported and (not n.citations or not set(n.citations).issubset(cited)):
                    raise ValueError('Supported need lacks a grounded claim')
            if not any(n.supported for n in coverage) and claims:
                raise ValueError('Generation cannot override unsupported evidence gate')
        elif config.llm_provider not in {'extractive', 'openai_compatible'}:
            raise ValueError('Unknown LLM provider')
        else:
            warnings.append('Extractive mode returns source wording. Complex paraphrases and teaching transformations may require a configured provider.')
            seen = set()
            for need in needs:
                matched = []
                candidates = [(c, excerpt_for(need, c)) for c in by_need[need]]
                pattern = definition_pattern(need)
                candidates.sort(key=lambda pair: bool(pair[1] and pattern and pattern.search(pair[1])), reverse=True)
                for c, quote in candidates:
                    if quote and c.extraction_quality != 'LOW':
                        matched.append(c.chunk_id)
                        if normalize(quote) not in seen:
                            claims.append(Claim(text=quote, citations=[c.chunk_id], quotes={c.chunk_id: quote}))
                            seen.add(normalize(quote))
                        break
                coverage.append(Need(need=need, supported=bool(matched), citations=matched))
            validate_claims(claims, chunks)
        supported = sum(n.supported for n in coverage)
        status = 'ANSWERED' if supported == len(needs) else 'PARTIALLY_ANSWERED' if supported else 'NOT_COVERED'
        if not supported and any(c.extraction_quality == 'LOW' and set(tokens(question)) & set(tokens(c.text)) for c in chunks):
            status = 'LOW_QUALITY_SOURCE'
        cited_ids = {cid for claim in claims for cid in claim.citations}
        sources = sorted(chunks, key=lambda c: c.chunk_id not in cited_ids)
        text = '\n\n'.join(c.text for c in claims)
        if not text:
            text = 'I could not find sufficient evidence in your materials to answer this question.' if status == 'NOT_COVERED' else 'The relevant source is too uncertain to answer reliably. Inspect the original and review its transcription.'
        if status == 'PARTIALLY_ANSWERED':
            text += '\n\nSome requested parts are not covered by the available evidence.'
        study_format = 'exam' if action=='exam' else 'simple' if action=='simple' else 'compare' if query_intent=='COMPARISON' else 'paragraph'
        study_note = ''
        if config.llm_provider=='extractive':
            study_note = {'simple':'Simple view selects the core source statement; vocabulary remains the original author’s.', 'exam':f'Exam outline: {len(claims)} evidence-backed point(s). Missing details are not padded, and marks are not guaranteed.', 'compare':'Compare the supported source statements side by side. Differences beyond this evidence are not inferred.', 'paragraph':'Source wording is shown directly. Check the citation for full context.'}[study_format]
        return Answer(status=status, answer=text, claims=claims, coverage=coverage, missing_evidence=[n.need for n in coverage if not n.supported], sources=[source_view(c) for c in sources[:max(16,len(cited_ids))]], mode=config.llm_provider + ' / ' + index.mode, warnings=warnings, resolved_question=question, retrieval_ms=round(elapsed, 2),query_intent=query_intent,study_format=study_format,study_note=study_note)
    except Exception as exc:
        return Answer(status='ERROR', answer='The evidence provider failed or returned an invalid answer. No unverified answer was displayed.', warnings=warnings + [type(exc).__name__], mode=config.llm_provider, resolved_question=question, retrieval_ms=round(elapsed, 2))
