import pytest
from scripts.check_corpus import check
from eval.schema import Question, validate_dataset


def test_corpus_checker_does_not_count_chunks_as_pages(tmp_path):
    (tmp_path/'notes.md').write_text('# Heading\n'+('paragraph\n\n'*100),encoding='utf-8')
    report=check(tmp_path)
    assert report['counts']['markdown_text_files']==1
    assert report['physical_pages_slides_images']==0
    assert not report['automated_pass']
    assert report['manual_verification_required']


def test_multi_requires_different_documents():
    with pytest.raises(ValueError,match='DIFFERENT'):
        Question(id='q',question='Compare the source concepts',type='multi_doc',answerable=True,expected_sources=[{'file':'a.pdf','page':1},{'file':'a.pdf','page':2}],expected_keywords=['term'],rationale='test')


def test_official_gate_rejects_missing_questions():
    with pytest.raises(ValueError,match='exactly 10'):
        validate_dataset([])
