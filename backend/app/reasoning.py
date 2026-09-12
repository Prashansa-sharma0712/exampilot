import re
from time import perf_counter
from .models import Answer, Claim, Need
from .retrieval import tokens


def normalize(text):
    return re.sub(r'\s+', ' ', text).strip().casefold()


def decompose(question):
    clean = question.strip().rstrip('?')
    # Explicit conjunctions and comparisons; never assume a related aspect is covered.
    clean = re.sub(r'^(compare|contrast)\s+', '', clean, flags=re.I)
    parts = re.split(r'\s+(?:and|versus|vs\.?|with)\s+|\s*;\s*', clean, flags=re.I)
    return [p.strip() for p in parts if p.strip()][:8] or [clean]


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
    if len(candidates) < 2:
        lines = chunk.text.splitlines()
        candidates += ['\n'.join(lines[i:i+6]) for i in range(len(lines))]
    best = None
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
        if not re.search(r'\b(is|are|means|used|uses|has|have|can|cannot|must|requires|provides|contains|allows|stores|defines|reduces|increases|depends|occurs|refers|called|represents|consists|does|do|shall|will)\b', quote, re.I):
            continue
        if best is None or len(quote) < len(best):
            best = quote
    return best


def source_view(c):
    return {**c.model_dump(exclude={'original_asset_path'}), 'location': c.location, 'preview_url': f'/api/source/{c.chunk_id}/preview', 'original_url': f'/api/source/{c.chunk_id}/original'}


def answer_question(question, index, config, document_id=None, source_type=None, action='ask'):
    start = perf_counter()
    needs = decompose(question)
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
                for c in by_need[need]:
                    quote = excerpt_for(need, c)
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
        return Answer(status=status, answer=text, claims=claims, coverage=coverage, missing_evidence=[n.need for n in coverage if not n.supported], sources=[source_view(c) for c in sources[:16]], mode=config.llm_provider + ' / ' + index.mode, warnings=warnings, resolved_question=question, retrieval_ms=round(elapsed, 2))
    except Exception as exc:
        return Answer(status='ERROR', answer='The evidence provider failed or returned an invalid answer. No unverified answer was displayed.', warnings=warnings + [type(exc).__name__], mode=config.llm_provider, resolved_question=question, retrieval_ms=round(elapsed, 2))
