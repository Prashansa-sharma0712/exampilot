import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import settings, ROOT
from backend.app.store import Store
from backend.app.ingestion import ingest

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus', default=settings.corpus_dir)
    parser.add_argument('--database', default=str(settings.db_path))
    args = parser.parse_args()
    result = ingest(ROOT / args.corpus, Store(Path(args.database)), settings)
    out = ROOT / 'data' / 'ingestion-report.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result['errors']))
