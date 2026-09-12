import threading
from contextlib import asynccontextmanager
from pathlib import Path
import pymupdf as fitz
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from .config import settings, ROOT
from .models import AskRequest, Answer
from .store import Store
from .study import Study
from .retrieval import Index
from .reasoning import answer_question, source_view
from .ingestion import ingest, digest, EXTENSIONS, IMAGES


def create_app(config=settings):
    store = Store(config.db_path)
    study = Study(store)
    state = {'index': None}
    lock = threading.RLock()

    def index():
        with lock:
            if state['index'] is None:
                state['index'] = Index(store.chunks(), config)
            return state['index']

    app = FastAPI(title='ExamPilot', version='0.1.0')
    app.state.store = store
    app.state.study = study

    @app.get('/api/health')
    def health():
        current = state['index']
        return {'status': 'ok', 'documents': len(store.documents()), 'provider': config.llm_provider, 'retrieval': current.mode if current else 'not_loaded', 'corpus': config.corpus.name, 'warning': current.warning if current else ''}

    @app.post('/api/session')
    def new_session():
        return {'session_id': study.session()}

    @app.get('/api/session/{session_id}')
    def session(session_id: str):
        return {'session_id': session_id, 'messages': study.history(session_id)}

    @app.get('/api/documents')
    def documents():
        return [{k: v for k, v in d.items() if k not in {'root', 'hash'}} for d in store.documents()]

    @app.post('/api/ingest')
    def ingest_local():
        with lock:
            result = ingest(config.corpus, store, config)
            state['index'] = None
        return result

    @app.post('/api/upload')
    def upload(file: UploadFile = File(...)):
        name = Path((file.filename or '').replace('\\', '/')).name
        if Path(name).suffix.lower() not in EXTENSIONS or name.startswith('.'):
            raise HTTPException(400, 'Unsupported filename or source type')
        target = config.corpus / 'uploads' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise HTTPException(409, 'A file with this name already exists; rename it before uploading')
        size = 0
        try:
            with target.open('xb') as output:
                while block := file.file.read(1024 * 1024):
                    size += len(block)
                    if size > 100 * 1024 * 1024:
                        raise HTTPException(413, 'Maximum file size is 100 MB')
                    output.write(block)
            return ingest_local()
        except Exception:
            target.unlink(missing_ok=True)
            raise

    @app.post('/api/ask', response_model=Answer)
    @app.post('/api/study/action', response_model=Answer)
    def ask(request: AskRequest):
        sid = study.session(request.session_id)
        resolved = study.resolve(sid, request.question, request.action)
        action = 'compare' if 'make a table' in request.question.lower() else request.action
        answer = answer_question(resolved, index(), config, request.document_id, request.source_type, action)
        answer.session_id = sid
        study.record(sid, request.question, answer)
        return answer

    @app.get('/api/exam-sprint/{session_id}')
    def sprint(session_id: str):
        return study.sprint(session_id)

    class SessionRequest(BaseModel):
        session_id: str

    @app.post('/api/revision/save')
    def save(request: SessionRequest):
        try:
            return study.save(request.session_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    @app.post('/api/quiz/generate')
    def quiz(request: SessionRequest):
        latest = study.latest(request.session_id)
        if not latest:
            raise HTTPException(400, 'Ask a supported question first')
        # Fresh retrieval: old messages are never used as evidence for a new quiz.
        fresh = answer_question(latest.resolved_question, index(), config)
        try:
            return study.quiz(request.session_id, fresh)
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    class QuizAnswer(SessionRequest):
        quiz_id: str
        answer: str = Field(min_length=1, max_length=2000)

    @app.post('/api/quiz/answer')
    def grade(request: QuizAnswer):
        try:
            return study.grade(request.session_id, request.quiz_id, request.answer)
        except ValueError as exc:
            raise HTTPException(404, str(exc))

    def source(chunk_id):
        c = store.chunk(chunk_id)
        if not c:
            raise HTTPException(404, 'Source not found')
        path = Path(c.original_asset_path).resolve()
        if not path.is_relative_to(config.corpus) or not path.is_file():
            raise HTTPException(404, 'Original source unavailable')
        return c, path

    @app.get('/api/source/{chunk_id}')
    def source_metadata(chunk_id: str):
        c, _ = source(chunk_id)
        return source_view(c)

    @app.get('/api/source/{chunk_id}/original')
    def original(chunk_id: str):
        _, path = source(chunk_id)
        return FileResponse(path, filename=path.name, content_disposition_type='inline' if path.suffix.lower() == '.pdf' else 'attachment')

    @app.get('/api/source/{chunk_id}/preview')
    def preview(chunk_id: str):
        c, path = source(chunk_id)
        if path.suffix.lower() in IMAGES:
            return FileResponse(path)
        if path.suffix.lower() == '.pdf':
            with fitz.open(path) as pdf:
                if not c.page or c.page > len(pdf):
                    raise HTTPException(404, 'Page no longer exists; re-ingest the source')
                return Response(pdf[c.page - 1].get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).tobytes('png'), media_type='image/png')
        if path.suffix.lower() == '.ppt':
            image = ROOT / 'data/converted' / digest(path) / f'slide-{c.slide}.png'
            if image.exists():
                return FileResponse(image)
        raise HTTPException(404, 'Visual preview unavailable; inspect extracted text or download the original')

    return app


app = create_app()
