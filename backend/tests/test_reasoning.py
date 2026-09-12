import pytest
from backend.app.config import Settings
from backend.app.models import Chunk, Claim
from backend.app.retrieval import Index
from backend.app.reasoning import answer_question, validate_claims


def c(cid, text, quality='HIGH'):
    return Chunk(chunk_id=cid, document_id=cid, document_name=cid+'.pdf', page=2, text=text, source_type='pdf', original_asset_path='test.pdf', extraction_quality=quality)


@pytest.fixture
def index():
    return Index([c('a', 'Encapsulation is the bundling of state and methods in one class.'), c('b', 'Inheritance allows a class to reuse behavior from another class.')], Settings(embedding_provider='none'))


def test_answer_partial_refusal_and_multi(index):
    config = Settings(embedding_provider='none')
    assert answer_question('What is encapsulation?', index, config).status == 'ANSWERED'
    partial = answer_question('Encapsulation and garbage collection', index, config)
    assert partial.status == 'PARTIALLY_ANSWERED'
    multi = answer_question('Compare encapsulation and inheritance', index, config)
    assert multi.status == 'ANSWERED'
    assert {cid for claim in multi.claims for cid in claim.citations} == {'a', 'b'}
    assert answer_question('What is encapsulation overhead?', index, config).status == 'NOT_COVERED'


def test_invalid_citations_rejected():
    with pytest.raises(ValueError, match='Unknown'):
        validate_claims([Claim(text='invented', citations=['missing'], quotes={'missing':'long enough invented quote'})], [])
    with pytest.raises(ValueError, match='not present'):
        validate_claims([Claim(text='invented', citations=['a'], quotes={'a':'invented quotation here'})], [c('a','Real source text here.')])


def test_empty_and_low_quality():
    config = Settings(embedding_provider='none')
    assert answer_question('arrays', Index([], config), config).status == 'NOT_COVERED'
    idx = Index([c('a', 'An array is a collection of elements of the same type.', 'LOW')], config)
    assert answer_question('What is an array?', idx, config).status == 'LOW_QUALITY_SOURCE'


def test_provider_failure_and_malformed_json(index, monkeypatch):
    from backend.app import providers
    monkeypatch.setattr(providers, 'completion', lambda *a, **k: {'nonsense': True})
    config = Settings(llm_provider='openai_compatible', embedding_provider='none')
    answer = answer_question('encapsulation', index, config)
    assert answer.status == 'ERROR' and not answer.claims


def test_topic_mention_is_not_support():
    config = Settings(embedding_provider='none')
    idx = Index([c('a', 'Topics: encapsulation, inheritance, polymorphism.')], config)
    assert answer_question('Explain encapsulation', idx, config).status == 'NOT_COVERED'
