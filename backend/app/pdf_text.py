"""Recover explicit hex glyph-name mappings; never infer letters from course context."""
import re


def page_text(page):
    repaired = False
    for xref, _, _, name, *_ in page.get_fonts(full=True):
        kind, value = page.parent.xref_get_key(xref, 'Encoding')
        encoding = page.parent.xref_object(int(value.split()[0])) if kind == 'xref' else value
        match = re.search(r'/Differences\s*\[([^]]*)\]', encoding, re.S)
        if not match:
            continue
        mapping, code = {}, 0
        for token in re.findall(r'/[^\s/]+|\d+', match[1]):
            if token.isdigit():
                code = int(token)
            else:
                glyph = re.fullmatch(r'/G([0-9A-Fa-f]{2,4})', token)
                if glyph:
                    decoded = chr(int(glyph[1], 16))
                    mapping[code] = decoded
                code += 1
        if mapping:
            # Add a ToUnicode map to the in-memory document only. Mapping after
            # extraction loses glyph codes that the extractor treats as whitespace.
            if page.parent.xref_get_key(xref, 'ToUnicode')[0] == 'null':
                pairs = '\n'.join(f'<{k:02X}> <{ord(v):04X}>' for k, v in mapping.items())
                cmap = ('/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n'
                        '/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n'
                        '/CMapName /Recovered def\n/CMapType 2 def\n1 begincodespacerange\n<00> <FF>\nendcodespacerange\n'
                        + str(len(mapping)) + ' beginbfchar\n' + pairs + '\nendbfchar\nendcmap\nCMapName currentdict /CMap defineresource pop\nend\nend')
                target = page.parent.get_new_xref()
                page.parent.update_object(target, '<<>>')
                page.parent.update_stream(target, cmap.encode('ascii'))
                page.parent.xref_set_key(xref, 'ToUnicode', f'{target} 0 R')
            repaired = True
    return page.get_text(sort=True).strip(), 'native_glyph_mapping' if repaired else 'native'


def broken_text(text):
    controls = sum(ord(c) < 32 and c not in '\n\r\t' for c in text)
    return len(re.sub(r'\W', '', text)) < 40 or controls > max(5, len(text) * .02) or text.count('\ufffd') > 5

