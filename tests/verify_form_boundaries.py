"""Field detection preserves labels, punctuation and copy-count wording."""
import tempfile
from pathlib import Path

from docx import Document
from openpyxl import Workbook

from office_forms import extra_fields
from word_fields import analyze_word

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    for line in ('Дополнительные сведения:\tзначение',
                 '\tДополнительные сведения:\tзначение'):
        document = Document()
        document.add_paragraph('АКТ освидетельствования скрытых работ')
        document.add_paragraph(line)
        path = root/'notes.docx'
        document.save(path)
        field = analyze_word(path)['fields']['notes']
        assert field['value'] == 'значение', field
        assert all('сведения' not in part['sample'] and ':' not in part['sample']
                   for part in field['segments']), field

    for gap in (' ', '     ', '___', ' 12 '):
        document = Document()
        document.add_paragraph('АКТ освидетельствования скрытых работ')
        document.add_paragraph('Акт составлен в'+gap+'экземплярах')
        path = root/'copies.docx'
        document.save(path)
        field = analyze_word(path)['fields']['copies']
        assert field['kind'] == 'number'
        assert field['value'] == ('12' if '12' in gap else ''), field

    for value in ('9. Акт составлен в  экземплярах.',
                  '9. Акт составлен в 3-х экземплярах.'):
        workbook = Workbook()
        workbook.active['A1'] = value
        path = root/'copies.xlsx'
        workbook.save(path)
        field = extra_fields(path)['copies']
        filled = field['prefix']+'12'+field['suffix']
        expected = '9. Акт составлен в 12'+('-х' if '-х' in value else '')+' экземплярах.'
        assert filled == expected, (filled, expected)

print('PASS field boundaries, labels, punctuation and copy-count separators')
