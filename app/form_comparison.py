"""Compare a blank form with a user-selected filled copy for manual binding."""
import re
from difflib import SequenceMatcher


def word_candidates(blank, filled):
    from word_fields import caption, calculated, text

    paragraphs = blank._element.body.xpath('.//w:p')
    other = filled._element.body.xpath('.//w:p')
    def units(nodes):
        return [(text(p), bool(p.xpath('./ancestor::w:tc'))) for p in nodes]

    left, right = units(paragraphs), units(other)
    def anchors(values):
        return [(' '.join(value.split()), table) for value, table in values]

    match = SequenceMatcher(None, anchors(left), anchors(right), autojunk=False)
    if sum(n for i, j, n in match.get_matching_blocks()
           for value, _ in left[i:i+n] if value.strip()) == 0:
        return {}
    proposals = {}
    for tag, a, b, c, d in match.get_opcodes():
        if tag != 'replace' or b-a != d-c:
            continue
        for i, j in zip(range(a,b), range(c,d)):
            value, table = left[i]
            example, example_table = right[j]
            if table != example_table or not example.strip() or caption(example) or caption(value) or calculated(paragraphs[i]):
                continue
            if not value.strip():
                proposals[i] = (0, len(value))
                continue
            spans = []
            for gap in re.finditer(r'[^\S\r\n\t]+', value):
                prefix, suffix = value[:gap.start()], value[gap.end():]
                if example.startswith(prefix) and example.endswith(suffix):
                    inserted = example[len(prefix):len(example)-len(suffix)]
                    if inserted.strip():
                        spans.append(gap.span())
            if len(spans) == 1:
                proposals[i] = spans[0]
    return proposals


def excel_candidates(blank, filled):
    from office_forms import instruction

    def geometry(sheet):
        return sorted(str(area) for area in sheet.merged_cells.ranges)

    if geometry(blank) != geometry(filled):
        return set()
    unchanged = sum(isinstance(c.value, str) and c.value.strip() and
                    c.value == filled[c.coordinate].value for row in blank for c in row)
    if unchanged < 2:
        return set()
    return {c.coordinate for row in blank for c in row
            if c.__class__.__name__ != 'MergedCell' and
            (c.value is None or isinstance(c.value, str) and not c.value.strip()) and
            (example := filled[c.coordinate]).data_type != 'f' and
            example.value is not None and str(example.value).strip() and
            not instruction(example.value)}
