import hashlib
import re
from collections import defaultdict
import numpy as np
from rank_bm25 import BM25Okapi
from .config import ROOT

STOP = set('a an the is are was were be been being of to in on at for from with by as and or what which how why when where does do did can could would should explain describe define give me tell about please that this it these those more simply now into turn mark answer compare versus vs according notes material course'.split())
STOP.update('definition definitions discuss outline summarize mean contrast'.split())
PREDICATES = r'is|are|means|refers to|stores|uses|allows|represents|consists of|divides|combines|explores|halves|changes|returns|removes|adds|tracks|maps|connects|provides|contains|requires|reduces|increases|depends|occurs|defines|stops'


def tokens(text):
    words = re.findall(r'[a-zA-Z][a-zA-Z0-9_-]*|\d+', text.lower())
    def singular(w):
        if w.endswith('classes'): return w[:-2]
        if len(w)>4 and w.endswith('ies'): return w[:-3]+'y'
        if len(w)>4 and w.endswith('s') and not w.endswith(('ss','us','is')): return w[:-1]
        return w
    return [singular(w) for w in words if w not in STOP]


def definition_pattern(query):
    terms = tokens(query)
    if not 1 <= len(terms) <= 4:
        return None
    phrase = r'\s+'.join(re.escape(t)+(r'(?:es)?' if t.endswith('ss') else r's?') for t in terms)
    return re.compile(r'\b' + phrase + r'\s+(?:\w+ly\s+)?(?:' + PREDICATES + r')\b', re.I)


class Index:
    def __init__(self, chunks, config):
        self.chunks = chunks
        self.config = config
        self.tokenized = [tokens(c.text) or ['__empty__'] for c in chunks]
        self.bm25 = BM25Okapi(self.tokenized) if chunks else None
        self.encoder = None
        self.vectors = None
        self.warning = ''
        self.mode = 'bm25'
        if chunks and config.embedding_provider == 'sentence_transformers':
            try:
                from sentence_transformers import SentenceTransformer
                cache = ROOT / '.cache' / 'models'
                self.encoder = SentenceTransformer(config.embedding_model, cache_folder=str(cache), local_files_only=True)
                fingerprint = hashlib.sha256((config.embedding_model + ''.join(c.chunk_id for c in chunks)).encode()).hexdigest()
                vector_path = ROOT / 'data' / 'vectors' / f'{fingerprint}.npy'
                vector_path.parent.mkdir(parents=True, exist_ok=True)
                if vector_path.exists():
                    self.vectors = np.load(vector_path, allow_pickle=False)
                else:
                    self.vectors = self.encoder.encode([c.text for c in chunks], normalize_embeddings=True, show_progress_bar=False)
                    np.save(vector_path, self.vectors)
                self.mode = 'hybrid_bm25_semantic_rrf'
            except Exception as exc:
                self.encoder = None
                self.warning = f'Semantic embeddings unavailable ({type(exc).__name__}); BM25-only fallback. Run scripts/download_model.py.'

    def search(self, query, limit=12, document_id=None, source_type=None):
        if not self.chunks:
            return []
        allowed = [i for i, c in enumerate(self.chunks) if (not document_id or c.document_id == document_id) and (not source_type or c.source_type == source_type)]
        lexical = self.bm25.get_scores(tokens(query))
        ranks = [sorted(allowed, key=lambda i: lexical[i], reverse=True)]
        if self.encoder is not None:
            try:
                vector = self.encoder.encode([query], normalize_embeddings=True)[0]
                scores = self.vectors @ vector
                ranks.append(sorted(allowed, key=lambda i: scores[i], reverse=True))
            except Exception:
                self.encoder = None
                self.mode = 'bm25'
                self.warning = 'Semantic query encoding failed; using BM25-only fallback.'
        fusion = defaultdict(float)
        for rank in ranks:
            for n, i in enumerate(rank[:40], 1):
                fusion[i] += 1 / (60 + n)
        q = set(tokens(query))
        definition = definition_pattern(query)
        if definition:
            for i in allowed:
                if definition.search(self.chunks[i].text):
                    fusion[i] += 1 / 61
        # Lightweight lexical rerank is explicit; it is not an entailment model.
        order = sorted(fusion, key=lambda i: (bool(definition and definition.search(self.chunks[i].text)), len(q & set(self.tokenized[i])) / max(len(q), 1), fusion[i]), reverse=True)
        selected, seen, per_doc = [], set(), defaultdict(int)
        for i in order:
            chunk = self.chunks[i]
            normalized = re.sub(r'\s+', ' ', chunk.text.strip().lower())
            if not normalized or normalized in seen:
                continue
            if per_doc[chunk.document_id] >= max(3, limit // 2) and len({self.chunks[j].document_id for j in order}) > 1:
                continue
            seen.add(normalized)
            per_doc[chunk.document_id] += 1
            selected.append(chunk)
            if len(selected) == limit:
                break
        # Expand only lexically relevant immediate neighbors within the same source.
        for hit in list(selected[:3]):
            unit = hit.page or hit.slide
            if not unit:
                continue
            for c in self.chunks:
                if c.document_id == hit.document_id and abs((c.page or c.slide or -99) - unit) == 1 and c.chunk_id not in {s.chunk_id for s in selected}:
                    if len(q & set(tokens(c.text))) >= max(2, len(q) // 2):
                        selected.append(c)
        return selected[:limit + 3]
