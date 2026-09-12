from fastapi.testclient import TestClient
from backend.app.config import Settings
from backend.app.main import create_app


def client_for(tmp_path):
    corpus = tmp_path / 'corpus'
    corpus.mkdir()
    (corpus / 'notes.md').write_text('# Encapsulation\nEncapsulation is the bundling of state and methods inside a class.\n# Inheritance\nInheritance allows a class to reuse behavior from another class.', encoding='utf-8')
    config = Settings(corpus_dir=str(corpus), database_url='sqlite:///' + str(tmp_path / 'test.db'), embedding_provider='none')
    client = TestClient(create_app(config))
    assert client.post('/api/ingest').status_code == 200
    return client


def test_session_followup_quiz_and_sprint(tmp_path):
    client = client_for(tmp_path)
    answer = client.post('/api/ask', json={'question':'Explain encapsulation'}).json()
    assert answer['status'] == 'ANSWERED'
    sid = answer['session_id']
    follow = client.post('/api/study/action', json={'question':'Explain that more simply', 'session_id':sid, 'action':'simple'}).json()
    assert follow['resolved_question'] == 'Explain encapsulation'
    assert follow['claims']
    assert client.post('/api/revision/save', json={'session_id':sid}).status_code == 200
    quiz = client.post('/api/quiz/generate', json={'session_id':sid}).json()
    assert 'expected' not in quiz
    result = client.post('/api/quiz/answer', json={'session_id':sid, 'quiz_id':quiz['id'], 'answer':'incorrect'}).json()
    assert result['correct'] is False
    # Replaying an attempt cannot inflate progress.
    client.post('/api/quiz/answer', json={'session_id':sid, 'quiz_id':quiz['id'], 'answer':'incorrect'})
    sprint = client.get('/api/exam-sprint/' + sid).json()
    assert len(sprint['weak']) == 1 and sprint['quiz_total'] == 1
    assert len(sprint['saved']) == 1
    assert len(client.get('/api/session/' + sid).json()['messages']) == 2


def test_source_and_input_errors(tmp_path):
    client = client_for(tmp_path)
    assert client.get('/api/health').json()['status'] == 'ok'
    assert client.post('/api/ask', json={'question':''}).status_code == 422
    assert client.get('/api/source/missing').status_code == 404
    assert client.post('/api/upload', files={'file':('bad.exe', b'bad')}).status_code == 400
    answer = client.post('/api/ask', json={'question':'Encapsulation'}).json()
    cid = answer['claims'][0]['citations'][0]
    assert client.get('/api/source/' + cid).json()['section'] == 'Encapsulation'
    assert client.get('/api/source/' + cid + '/original').status_code == 200
    assert client.get('/api/source/' + cid + '/preview').status_code == 404
