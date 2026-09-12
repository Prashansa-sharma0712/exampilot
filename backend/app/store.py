import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .models import Chunk


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, name TEXT UNIQUE, hash TEXT, info TEXT);
            CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, document_id TEXT, body TEXT);
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, context TEXT DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, session_id TEXT, question TEXT, answer TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS topics(session_id TEXT, topic TEXT, asked INTEGER DEFAULT 0, correct INTEGER DEFAULT 0, total INTEGER DEFAULT 0, updated TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(session_id,topic));
            CREATE TABLE IF NOT EXISTS quizzes(id TEXT PRIMARY KEY, session_id TEXT, topic TEXT, body TEXT, result TEXT);
            CREATE TABLE IF NOT EXISTS saved(id INTEGER PRIMARY KEY, session_id TEXT, body TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def chunks(self):
        with self.connect() as db:
            return [Chunk.model_validate_json(r['body']) for r in db.execute('SELECT body FROM chunks ORDER BY id')]

    def chunk(self, chunk_id):
        with self.connect() as db:
            row = db.execute('SELECT body FROM chunks WHERE id=?', (chunk_id,)).fetchone()
            return Chunk.model_validate_json(row['body']) if row else None

    def documents(self):
        with self.connect() as db:
            return [json.loads(r['info']) for r in db.execute('SELECT info FROM documents ORDER BY name')]

    def replace_document(self, info, chunks):
        with self.connect() as db:
            old = db.execute('SELECT id FROM documents WHERE name=?', (info['name'],)).fetchone()
            if old:
                db.execute('DELETE FROM chunks WHERE document_id=?', (old['id'],))
                db.execute('DELETE FROM documents WHERE id=?', (old['id'],))
            db.execute('INSERT INTO documents VALUES (?,?,?,?)', (info['id'], info['name'], info['hash'], json.dumps(info)))
            db.executemany('INSERT INTO chunks VALUES (?,?,?)', [(c.chunk_id, c.document_id, c.model_dump_json()) for c in chunks])
