"""Downloads public model weights only. Does not upload course material."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import settings, ROOT
from sentence_transformers import SentenceTransformer

if __name__ == '__main__':
    model = SentenceTransformer(settings.embedding_model, cache_folder=str(ROOT / '.cache' / 'models'))
    print('Model ready:', settings.embedding_model, model.get_sentence_embedding_dimension())
