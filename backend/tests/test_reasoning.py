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


def test_definition_prefers_actual_definition_over_related_fact():
    config = Settings(embedding_provider='none')
    idx = Index([c('a','The class has a performance limitation when copying large objects.'),c('b','A class is a programmer-defined data type with associated operations.')],config)
    answer = answer_question('What is a class?',idx,config)
    assert answer.status == 'ANSWERED'
    assert answer.claims[0].citations == ['b']
    idx = Index([c('a','The class has a performance limitation when copying large objects.')],config)
    assert answer_question('What is a class?',idx,config).status == 'NOT_COVERED'


def test_definition_does_not_select_conditional_special_case():
    config = Settings(embedding_provider='none')
    idx = Index([c('a','If its behavior is linear, a system is called a linear system.\n\nA system is a collection of connected elements that perform a function.')],config)
    answer = answer_question('What is a system?',idx,config)
    assert answer.status == 'ANSWERED'
    assert 'connected elements' in answer.claims[0].text


def test_descriptive_predicates_are_supported_without_copula():
    config=Settings(embedding_provider='none')
    idx=Index([c('a','A partition repeatedly divides a large storage region into smaller regions.')],config)
    assert answer_question('What is a partition?',idx,config).status == 'ANSWERED'


def test_query_aspects_and_study_formats(index):
    from backend.app.query import decompose
    assert decompose('Compare X and Y in terms of cost and failure') == ['X cost','X failure','Y cost','Y failure']
    config=Settings(embedding_provider='none')
    assert answer_question('Encapsulation',index,config,action='simple').study_format=='simple'
    exam=answer_question('Encapsulation',index,config,action='exam')
    assert exam.study_format=='exam' and 'not guaranteed' in exam.study_note
    assert answer_question('Compare encapsulation and inheritance',index,config).study_format=='compare'
