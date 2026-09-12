"""Rebuild the public, self-authored synthetic regression corpus; never touches private/."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSONS = [
    ('Array', 'An array stores elements in indexed positions of a fixed-size sequence.', 'Indexed lookup', 'Indexed lookup uses a position to access a particular element directly.'),
    ('Stack', 'A stack is a collection where the most recently added item is removed first.', 'Undo history', 'Undo history can use last-in-first-out ordering to reverse the latest recorded operation.'),
    ('Queue', 'A queue is a collection where the earliest added item is removed first.', 'Print scheduling', 'Print scheduling can use first-in-first-out ordering to serve waiting jobs in arrival order.'),
    ('Linked list', 'A linked list stores elements in nodes connected by references to other nodes.', 'Node insertion', 'Node insertion changes references to connect a new node into an existing chain.'),
    ('Binary search', 'Binary search repeatedly halves the search interval in an ordered collection.', 'Sorted input', 'Sorted input is required for the interval comparisons in the search example to be valid.'),
    ('Merge sort', 'Merge sort divides a sequence into smaller sequences and merges sorted results.', 'Merge operation', 'A merge operation combines two sorted sequences into one sorted sequence.'),
    ('Hash table', 'A hash table uses a hash function to select a storage position for a key.', 'Collision', 'A collision occurs when distinct keys map to the same storage position.'),
    ('Breadth-first search', 'Breadth-first search explores reachable vertices one distance level at a time.', 'Frontier queue', 'A frontier queue stores discovered vertices waiting to be explored in arrival order.'),
    ('Depth-first search', 'Depth-first search explores one branch before returning to try another branch.', 'Backtracking', 'Backtracking returns to a previous choice when the current branch cannot proceed.'),
    ('Recursion', 'Recursion is a technique in which a function calls itself on a smaller problem.', 'Base case', 'A base case stops further recursive calls and provides a direct result.'),
]

if __name__ == '__main__':
    corpus = ROOT / 'corpus/demo'
    corpus.mkdir(parents=True, exist_ok=True)
    for name, offset in [('concepts.md', 0), ('applications.md', 2)]:
        content = '\n\n'.join('# ' + row[offset] + '\n\n' + row[offset+1] for row in LESSONS)
        (corpus/name).write_text(content+'\n', encoding='utf-8')
    (corpus/'LICENSE').write_text('Self-created synthetic ExamPilot demonstration material. Released under CC0 1.0. Not real course material.\n', encoding='utf-8')
    rows=[]
    for i,(topic,definition,related,explanation) in enumerate(LESSONS,1):
        source={'file':'concepts.md','section':topic}
        common={'rationale':'Self-authored synthetic fixture; known contents, not human-verified real course ground truth.','verification':'synthetic_authored'}
        rows.append(dict(id=f's{i:02}',question=f'What is {topic.lower()}?',type='single_doc',answerable=True,expected_sources=[source],expected_keywords=[definition.split()[-2]],**common))
        rows.append(dict(id=f'm{i:02}',question=f'Explain {topic.lower()} and {related.lower()}',type='multi_doc',answerable=True,expected_sources=[source,{'file':'applications.md','section':related}],expected_keywords=[topic.lower(),related.lower()],**common))
        rows.append(dict(id=f'u{i:02}',question=f'What is the lock-free memory reclamation strategy for {topic.lower()}?',type='unsupported',answerable=False,expected_sources=[],expected_keywords=[],**common))
    (ROOT/'eval/demo_questions.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    print('Created two synthetic Markdown sources and 30 synthetic regression questions.')
