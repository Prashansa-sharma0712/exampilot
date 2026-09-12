import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.schema import validate_dataset

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('dataset',nargs='?',default='data/eval/questions.json')
    parser.add_argument('--allow-draft',action='store_true')
    args=parser.parse_args()
    try:
        questions=validate_dataset(json.loads(Path(args.dataset).read_text(encoding='utf-8-sig')),official=not args.allow_draft)
        print(f'Validated {len(questions)} questions. Label gate: '+('draft diagnostics' if args.allow_draft else 'human-verified labels'))
    except (ValueError,OSError) as exc:
        raise SystemExit(str(exc))
