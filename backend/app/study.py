import json
import re
import uuid
from .models import Answer
from .reasoning import normalize
from .retrieval import tokens


class Study:
    def __init__(self, store):
        self.store = store

    def session(self, session_id=None):
        session_id = session_id or str(uuid.uuid4())
        with self.store.connect() as db:
            db.execute('INSERT OR IGNORE INTO sessions(id) VALUES (?)', (session_id,))
        return session_id

    def resolve(self, session_id, question, action='ask'):
        with self.store.connect() as db:
            row = db.execute('SELECT context FROM sessions WHERE id=?', (session_id,)).fetchone()
        context = json.loads(row['context']) if row else {}
        subject = context.get('question', '')
        follow = bool(re.search(r'\b(that|this|it|these|those|more simply|make a table|5.mark|give an example)\b', question, re.I))
        if subject and (follow or (action != 'ask' and not tokens(question))):
            if re.search(r'compare\s+(?:it|that|this)?\s*with\s+', question, re.I):
                other = re.split(r'\bwith\b', question, maxsplit=1, flags=re.I)[-1]
                return f'{subject.rstrip("?")} and {other}'
            return subject + (' example' if action == 'example' or 'example' in question.lower() else '')
        return question

    def record(self, session_id, question, answer):
        with self.store.connect() as db:
            db.execute('INSERT INTO messages(session_id,question,answer) VALUES (?,?,?)', (session_id, question, answer.model_dump_json()))
            if answer.claims:
                topic = answer.resolved_question[:180]
                db.execute('UPDATE sessions SET context=? WHERE id=?', (json.dumps({'question': answer.resolved_question, 'topic': topic}), session_id))
                db.execute('INSERT INTO topics(session_id,topic,asked) VALUES (?,?,1) ON CONFLICT(session_id,topic) DO UPDATE SET asked=asked+1,updated=CURRENT_TIMESTAMP', (session_id, topic))

    def history(self, session_id):
        with self.store.connect() as db:
            return [{'question': r['question'], 'answer': json.loads(r['answer']), 'created': r['created']} for r in db.execute('SELECT * FROM messages WHERE session_id=? ORDER BY id', (session_id,))]

    def latest(self, session_id):
        with self.store.connect() as db:
            row = db.execute('SELECT answer FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 1', (session_id,)).fetchone()
        return Answer.model_validate_json(row['answer']) if row else None

    def save(self, session_id):
        answer = self.latest(session_id)
        if not answer or not answer.claims:
            raise ValueError('Ask a supported question before saving revision evidence')
        with self.store.connect() as db:
            db.execute('INSERT INTO saved(session_id,body) VALUES (?,?)', (session_id, answer.model_dump_json()))
        return {'saved': True}

    def quiz(self, session_id, answer):
        if not answer.claims:
            raise ValueError('No reliable course evidence available for a quiz')
        claim = answer.claims[0]
        text = claim.quotes[claim.citations[0]]
        subject_terms = set(tokens(answer.resolved_question))
        words = re.findall(r'\b[A-Za-z][A-Za-z-]{3,}\b', text)
        candidates = [w for w in words if w.lower() not in subject_terms and w.lower() in tokens(w)] or words
        if not candidates:
            raise ValueError('Evidence is not suitable for a cloze quiz')
        expected = max(candidates, key=len)
        question = 'Complete the exact course excerpt: ' + re.sub(r'\b' + re.escape(expected) + r'\b', '____', text, flags=re.I)
        quiz = {'id': str(uuid.uuid4()), 'question': question, 'expected': expected, 'topic': answer.resolved_question[:180], 'citations': claim.citations, 'evidence': text}
        with self.store.connect() as db:
            db.execute('INSERT INTO quizzes VALUES (?,?,?,?,NULL)', (quiz['id'], session_id, quiz['topic'], json.dumps(quiz)))
        return {k: v for k, v in quiz.items() if k not in {'expected', 'evidence'}}

    def grade(self, session_id, quiz_id, response):
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM quizzes WHERE id=? AND session_id=?', (quiz_id, session_id)).fetchone()
            if not row:
                raise ValueError('Quiz does not exist in this session')
            if row['result']:
                return json.loads(row['result'])
            quiz = json.loads(row['body'])
            correct = normalize(response).strip(' .!?') == normalize(quiz['expected'])
            result = {'correct': correct, 'student_answer': response, 'expected': quiz['expected'], 'evidence': quiz['evidence'], 'citations': quiz['citations'], 'grading': 'exact cloze match; not a semantic short-answer grader'}
            db.execute('UPDATE quizzes SET result=? WHERE id=?', (json.dumps(result), quiz_id))
            db.execute('INSERT INTO topics(session_id,topic,correct,total) VALUES (?,?,?,1) ON CONFLICT(session_id,topic) DO UPDATE SET correct=correct+excluded.correct,total=total+1,updated=CURRENT_TIMESTAMP', (session_id, quiz['topic'], int(correct)))
        return result

    def sprint(self, session_id):
        with self.store.connect() as db:
            topics = [dict(r) for r in db.execute('SELECT * FROM topics WHERE session_id=? ORDER BY updated DESC', (session_id,))]
            saved = [json.loads(r['body']) for r in db.execute('SELECT body FROM saved WHERE session_id=? ORDER BY id DESC', (session_id,))]
        for t in topics:
            t['status'] = 'STUDYING' if t['total'] == 0 else 'WEAK' if t['correct'] / t['total'] < .7 else 'MASTERED' if t['total'] >= 3 and t['correct'] == t['total'] else 'GOOD'
        weak = sorted([t for t in topics if t['status'] == 'WEAK'], key=lambda t: t['total'] - t['correct'], reverse=True)
        return {'topics': topics, 'weak': weak, 'strong': [t for t in topics if t['status'] in {'GOOD', 'MASTERED'}], 'saved': saved, 'quiz_correct': sum(t['correct'] for t in topics), 'quiz_total': sum(t['total'] for t in topics), 'recommended': (weak or topics or [None])[0], 'coverage_note': 'Progress reflects attempted quizzes, not complete syllabus coverage.'}
