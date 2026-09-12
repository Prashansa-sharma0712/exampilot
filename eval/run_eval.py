"""Measured proxy metrics, never an unreviewed semantic-correctness claim."""
import argparse
import hashlib
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.schema import validate_dataset
from backend.app.config import ROOT, Settings
from backend.app.store import Store
from backend.app.retrieval import Index
from backend.app.reasoning import answer_question, normalize


def location_key(source):
    return (source['document_name'], source.get('page'), source.get('slide'), source.get('section'))


def run(questions, store, config, official):
    start = time.perf_counter()
    index = Index(store.chunks(), config)
    records = []
    for q in questions:
        t = time.perf_counter()
        answer = answer_question(q.question, index, config)
        elapsed = (time.perf_counter() - t) * 1000
        cited_ids = {cid for claim in answer.claims for cid in claim.citations}
        cited = [s for s in answer.sources if s['chunk_id'] in cited_ids]
        expected = {(s.file, s.page, s.slide, s.section) for s in q.expected_sources}
        actual = {location_key(s) for s in cited}
        retrieved = {location_key(s) for s in answer.sources}
        files = {s['document_name'] for s in cited}
        correct_locations = expected.issubset(actual)
        keywords = all(normalize(w) in normalize(answer.answer) for w in q.expected_keywords)
        passed = (answer.status == 'ANSWERED' and correct_locations and keywords) if q.answerable else answer.status == 'NOT_COVERED'
        failure = None
        if not passed:
            failure = 'SUFFICIENCY_FALSE_POSITIVE' if not q.answerable else 'GENERATION_FAILURE' if answer.status == 'ERROR' else 'RETRIEVAL_FAILURE' if not expected.issubset(retrieved) else 'SUFFICIENCY_FALSE_NEGATIVE' if not answer.claims else 'SECOND_SOURCE_MISSING' if q.type == 'multi_doc' and len(files) < 2 else 'CITATION_FAILURE' if not correct_locations else 'ANSWER_KEYWORD_MISMATCH'
        records.append({'id':q.id,'type':q.type,'question':q.question,'passed_proxy':passed,'failure':failure,'status':answer.status,'answer':answer.answer,'expected_locations':[list(x) for x in expected],'actual_locations':[list(x) for x in actual],'correct_locations':correct_locations,'expected_files_found':{s.file for s in q.expected_sources}.issubset(files),'keyword_check':keywords,'recall_at_returned_k':len(expected & retrieved)/len(expected) if expected else None,'citation_hits':len(expected & actual),'citation_count':len(actual),'handwriting_expected':any(Path(s.file).suffix.lower() in {'.jpg','.jpeg','.png','.webp'} for s in q.expected_sources),'handwriting_retrieved':any(s['source_type']=='handwritten' for s in answer.sources),'retrieval_ms':answer.retrieval_ms,'answer_ms':round(elapsed,2),'mode':answer.mode,'warnings':answer.warnings})
    groups = {kind:{'passed':sum(r['passed_proxy'] for r in records if r['type']==kind),'total':sum(r['type']==kind for r in records)} for kind in ('single_doc','multi_doc','unsupported')}
    answerable = [r for r in records if r['type']!='unsupported']
    handwriting = [r for r in records if r['handwriting_expected']]
    return {'run_at':datetime.now(timezone.utc).isoformat(),'official_labels':official,'label_status':'human_verified' if official else 'DRAFT_OR_SYNTHETIC_DIAGNOSTIC','metric_limitations':'Answer success is a status + expected-keyword + exact-location proxy, not human semantic grading. Citation precision uses annotated expected locations; alternative valid sources can score as false positives. No hallucination-free claim is measured.','retrieval_mode':index.mode,'provider':config.llm_provider,'groups':groups,'exact_source_locations':{'passed':sum(r['correct_locations'] for r in answerable),'total':len(answerable)},'citation_precision_proxy':sum(r['citation_hits'] for r in answerable)/max(sum(r['citation_count'] for r in answerable),1),'mean_recall_at_returned_k':statistics.mean(r['recall_at_returned_k'] for r in answerable),'handwriting_retrieval':{'passed':sum(r['handwriting_retrieved'] for r in handwriting),'total':len(handwriting)},'mean_retrieval_ms':round(statistics.mean(r['retrieval_ms'] for r in records),2),'mean_answer_ms':round(statistics.mean(r['answer_ms'] for r in records),2),'elapsed_seconds':round(time.perf_counter()-start,2),'records':records}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--dataset',default='data/eval/questions.json')
    parser.add_argument('--database',default='data/exampilot.db')
    parser.add_argument('--output',default='data/eval/results.json')
    parser.add_argument('--allow-draft',action='store_true')
    parser.add_argument('--lexical-only',action='store_true')
    args=parser.parse_args()
    dataset=ROOT/args.dataset
    if not dataset.exists():
        raise SystemExit('Verified dataset absent. Review data/eval/questions_draft.json; see eval/README.md. No official metrics were produced.')
    rows=json.loads(dataset.read_text(encoding='utf-8-sig'))
    try:
        questions=validate_dataset(rows,official=not args.allow_draft)
    except ValueError as exc:
        raise SystemExit(str(exc))
    config=Settings(embedding_provider='none') if args.lexical_only else Settings()
    report=run(questions,Store(ROOT/args.database),config,not args.allow_draft)
    report['dataset_sha256']=hashlib.sha256(dataset.read_bytes()).hexdigest()
    report['documents']=[{'name':d['name'],'hash':d['hash'],'units':d['units']} for d in Store(ROOT/args.database).documents()]
    out=ROOT/args.output
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    out.with_name(out.stem+'-failures.json').write_text(json.dumps([r for r in report['records'] if not r['passed_proxy']],indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'records','documents'}},indent=2))
