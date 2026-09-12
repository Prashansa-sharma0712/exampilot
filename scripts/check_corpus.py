import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymupdf as fitz
from pptx import Presentation
from backend.app.config import ROOT, settings
from backend.app.ingestion import digest, IMAGES


def check(corpus):
    counts = dict(pdf_files=0, pdf_pages=0, slide_files=0, slides=0, markdown_text_files=0, handwritten_images=0)
    errors, inventory = [], []
    if not corpus.is_dir():
        errors.append('Corpus directory is missing')
    for path in sorted(corpus.rglob('*')):
        if not path.is_file() or not path.resolve().is_relative_to(corpus.resolve()):
            continue
        ext, units = path.suffix.lower(), 0
        try:
            if ext == '.pdf':
                counts['pdf_files'] += 1
                with fitz.open(path) as pdf:
                    units = len(pdf)
                counts['pdf_pages'] += units
            elif ext in {'.ppt', '.pptx'}:
                counts['slide_files'] += 1
                if ext == '.pptx':
                    units = len(Presentation(path).slides)
                else:
                    converted = ROOT / 'data/converted' / digest(path) / 'slides.tsv'
                    if converted.exists():
                        units = len(converted.read_text(encoding='utf-8').splitlines())
                    else:
                        import olefile
                        with olefile.OleFileIO(path) as ole:
                            props = ole.getproperties('\x05DocumentSummaryInformation')
                            units = props.get(7, 0)
                        if not isinstance(units, int) or units <= 0:
                            raise ValueError('Slide count unavailable; run local legacy conversion')
                counts['slides'] += units
            elif ext in {'.md', '.txt'}:
                counts['markdown_text_files'] += 1
                units = 1
            elif ext in IMAGES:
                counts['handwritten_images'] += 1
                units = 1
            else:
                continue
            inventory.append({'file': path.relative_to(corpus).as_posix(), 'units': units, 'format': ext})
        except Exception as exc:
            errors.append(f'{path.name}: {exc}')
    physical = counts['pdf_pages'] + counts['slides'] + counts['handwritten_images']
    requirements = {'60_physical_pages_slides': physical >= 60, 'pdf': counts['pdf_files'] > 0, 'slides': counts['slide_files'] > 0, 'markdown_or_text': counts['markdown_text_files'] > 0, 'two_handwritten_images': counts['handwritten_images'] >= 2}
    return {'corpus': str(corpus), 'counts': counts, 'physical_pages_slides_images': physical, 'approx_total_including_text_files': physical + counts['markdown_text_files'], 'format_diversity': sum([counts['pdf_files'] > 0, counts['slide_files'] > 0, counts['markdown_text_files'] > 0, counts['handwritten_images'] > 0]), 'automated_requirements': requirements, 'automated_pass': all(requirements.values()) and not errors, 'manual_verification_required': ['Confirm these are real course materials and form the intended course.', 'Confirm image files are genuine handwriting photographs (extensions alone are not proof).', 'Confirm at least one handwriting page is genuinely difficult.', 'Confirm a diagram, table or equation in the original sources.', 'Confirm access and redistribution rights; keep private material out of Git.'], 'inventory': inventory, 'errors': errors}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check real local corpus without publishing or changing it.')
    parser.add_argument('--corpus', default=settings.corpus_dir)
    parser.add_argument('--output', default='data/corpus-report.json')
    args = parser.parse_args()
    report = check((ROOT / args.corpus).resolve())
    target = ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['automated_pass'] else 1)
