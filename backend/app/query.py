import re


def intent(question, action='ask'):
    q=question.lower()
    if action=='exam' or re.search(r'5.mark|exam answer',q): return 'EXAM_ANSWER'
    if action=='compare' or re.search(r'\bcompare|\bcontrast|\bversus|make a table',q): return 'COMPARISON'
    if action=='example' or 'example' in q: return 'EXAMPLE'
    if action=='simple' or re.search(r'\b(that|this|it)\b|more simply',q): return 'FOLLOW_UP'
    if re.search(r'^what (is|are)|^define|\bdefinition\b|\bmean\??$',q): return 'DEFINITION'
    if ' and ' in q or ';' in q: return 'MULTI_SOURCE'
    if re.search(r'^explain|^describe|^how|^why',q): return 'EXPLANATION'
    return 'OTHER'


def decompose(question):
    clean=question.strip().rstrip('?')
    detailed=re.match(r'^(?:compare|contrast) (.+?) (?:and|versus|vs\.?|with) (.+?) (?:in terms of|on) (.+)$',clean,re.I)
    if detailed:
        aspects=[s.strip() for s in re.split(r',|\band\b',detailed[3]) if s.strip()]
        return [entity.strip()+' '+aspect for entity in detailed.group(1,2) for aspect in aspects]
    clean=re.sub(r'^(compare|contrast)\s+','',clean,flags=re.I)
    parts=re.split(r'\s+(?:and|versus|vs\.?|with)\s+|\s*;\s*',clean,flags=re.I)
    return [p.strip() for p in parts if p.strip()] or [clean]
