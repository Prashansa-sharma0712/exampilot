"""Page-preserving native extraction; private derivatives never leave data/."""
import hashlib
import json
import re
from pathlib import Path
import pymupdf as fitz
from PIL import Image, ImageOps
from pptx import Presentation
from .config import ROOT
from .models import Chunk
from .pdf_text import page_text, broken_text

EXTENSIONS = {'.pdf', '.pptx', '.ppt', '.md', '.txt', '.jpg', '.jpeg', '.png', '.webp'}
IMAGES = {'.jpg', '.jpeg', '.png', '.webp'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def image_text(path: Path, config, sidecars=True):
    # A reviewed transcription is an explicit local fallback, never presented as OCR.
    sidecar = path.with_suffix(path.suffix + '.transcript.json')
    if sidecars and sidecar.exists():
        data = json.loads(sidecar.read_text(encoding='utf-8'))
        if data.get('source_sha256') != digest(path):
            raise ValueError('Transcription does not match current image hash')
        if data.get('reviewed') is True and data.get('reviewer'):
            return data['text'], data.get('quality', 'MEDIUM'), data.get('method', 'reviewed_transcription')
    if config.vision_provider == 'openai_compatible':
        from .providers import vision_extract
        return vision_extract(path, config)
    try:
        import pytesseract
        with Image.open(path) as source:
            prepared = ImageOps.autocontrast(ImageOps.grayscale(ImageOps.exif_transpose(source)))
            text = pytesseract.image_to_string(prepared).strip()
        # Local OCR is not a reliable handwriting assessor: require review.
        return text, 'LOW', 'tesseract_unreviewed'
    except Exception:
        try:
            from rapidocr_onnxruntime import RapidOCR
            global _ocr
            if '_ocr' not in globals():
                _ocr = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=2)
            result, _ = _ocr(str(path))
            return '\n'.join(r[1] for r in (result or [])), 'LOW' if sidecars else 'MEDIUM', 'rapidocr_unreviewed'
        except Exception:
            return '', 'LOW', 'ocr_unavailable'


def converted_ppt(path):
    target = ROOT / 'data' / 'converted' / (digest(path) + '.pptx')
    if not target.exists():
        raise ValueError('Legacy PPT needs local conversion: run scripts/convert_ppt.ps1 first')
    return target


def sections(text):
    heading, lines, chain = 'Introduction', [], []
    for line in text.splitlines():
        match = re.match(r'^(#{1,6})\s+(.+)', line)
        if match:
            if '\n'.join(lines).strip():
                yield heading, '\n'.join(lines).strip()
            depth = len(match[1])
            chain = chain[:depth - 1] + [match[2].strip()]
            heading, lines = ' / '.join(chain), []
        else:
            lines.append(line)
    if '\n'.join(lines).strip():
        yield heading, '\n'.join(lines).strip()


def extract(path: Path, config):
    ext = path.suffix.lower()
    if ext == '.pdf':
        file_hash = digest(path)
        with fitz.open(path) as pdf:
            for n, page in enumerate(pdf, 1):
                text, method = page_text(page)
                quality = 'HIGH'
                if broken_text(text):
                    preview = ROOT / 'data' / 'ocr' / file_hash / f'{n}.png'
                    preview.parent.mkdir(parents=True, exist_ok=True)
                    page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(preview)
                    text, quality, method = image_text(preview, config, sidecars=False)
                yield dict(page=n, text=text, source_type='pdf', extraction_quality=quality, extraction_method=method)
    elif ext in {'.ppt', '.pptx'}:
        legacy = ROOT / 'data/converted' / digest(path) / 'slides.tsv'
        if ext == '.ppt' and legacy.exists():
            import base64
            for line in legacy.read_text(encoding='utf-8').splitlines():
                number, encoded = line.split('\t', 1)
                text = base64.b64decode(encoded).decode('utf-8')
                yield dict(slide=int(number), heading=text.splitlines()[0] if text.strip() else None, text=text, source_type='pptx', extraction_method='apache_poi_legacy')
            return
        prs = Presentation(converted_ppt(path) if ext == '.ppt' else path)
        for n, slide in enumerate(prs.slides, 1):
            values = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    values.append(shape.text)
                if shape.has_table:
                    values.extend(' | '.join(c.text for c in row.cells) for row in shape.table.rows)
            title = slide.shapes.title.text if slide.shapes.title else None
            yield dict(slide=n, heading=title, text='\n\n'.join(values), source_type='pptx')
    elif ext in {'.md', '.txt'}:
        for heading, text in sections(path.read_text(encoding='utf-8-sig')):
            yield dict(section=heading, heading=heading, text=text, source_type='markdown' if ext == '.md' else 'text')
    elif ext in IMAGES:
        text, quality, method = image_text(path, config)
        yield dict(page=1, text=text, source_type='handwritten', extraction_quality=quality, extraction_method=method)
    else:
        raise ValueError('Unsupported file format')


def chunk_record(record, base):
    # Keep slides and handwriting intact. Group paragraphs for long PDF/MD sections.
    text = record['text']
    groups = [text]
    if record['source_type'] not in {'pptx', 'handwritten'} and len(text.split()) > 650:
        groups, current = [], []
        for paragraph in re.split(r'\n\s*\n', text):
            # Long unbroken paragraphs fall back to sentence boundaries.
            parts = re.split(r'(?<=[.!?])\s+', paragraph) if len(paragraph.split()) > 650 else [paragraph]
            for part in parts:
                if sum(len(p.split()) for p in current) + len(part.split()) > 650 and current:
                    groups.append('\n\n'.join(current))
                    current = current[-1:] if len(current[-1].split()) < 100 else []
                current.append(part)
        if current:
            groups.append('\n\n'.join(current))
    for i, group in enumerate(groups):
        payload = {**base, **record, 'text': group}
        identity = f"{base['document_id']}:{record.get('page')}:{record.get('slide')}:{record.get('section')}:{i}:{group}"
        payload['chunk_id'] = hashlib.sha256(identity.encode()).hexdigest()[:24]
        yield Chunk(**payload)


def ingest(corpus: Path, store, config):
    corpus = corpus.resolve()
    report = {'root': str(corpus), 'ingested': [], 'skipped': [], 'errors': []}
    existing = {d['name']: d for d in store.documents()}
    if not corpus.is_dir():
        report['errors'].append({'file': str(corpus), 'error': 'Corpus directory does not exist'})
        return report
    for path in sorted(corpus.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        if not path.resolve().is_relative_to(corpus):
            report['errors'].append({'file': path.name, 'error': 'Symlink outside corpus rejected'})
            continue
        name = path.relative_to(corpus).as_posix()
        try:
            file_hash = digest(path)
            sidecar = path.with_suffix(path.suffix + '.transcript.json')
            fingerprint = file_hash + (digest(sidecar) if sidecar.exists() else '')
            fingerprint += ':v2:' + config.vision_provider
            if existing.get(name, {}).get('hash') == fingerprint:
                report['skipped'].append(name)
                continue
            doc_id = hashlib.sha256((str(corpus) + name).encode()).hexdigest()[:20]
            base = dict(document_id=doc_id, document_name=name, original_asset_path=str(path.resolve()))
            records = list(extract(path, config))
            chunks = [c for record in records for c in chunk_record(record, base)]
            info = dict(id=doc_id, name=name, hash=fingerprint, source_type=chunks[0].source_type if chunks else path.suffix, units=len(records), chunks=len(chunks), low_quality=sum(c.extraction_quality == 'LOW' for c in chunks), root=str(corpus))
            store.replace_document(info, chunks)
            report['ingested'].append(info)
        except Exception as exc:
            report['errors'].append({'file': name, 'error': str(exc)[:300]})
    return report
