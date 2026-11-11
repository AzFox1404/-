"""Office layout regression on generated files, with no private fixtures."""
from pathlib import Path
import json
import subprocess
import tempfile
from openpyxl import Workbook, load_workbook
from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement
from openpyxl.styles import Font
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_LINE_SPACING
from word_fields import bookmark
from app_paths import APP_DIR
import pymupdf

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    book = Workbook()
    sheet = book.active
    sheet.merge_cells('A1:D1')
    sheet['A1'] = 'Начальное значение'
    sheet['A1'].font = Font(name='Arial', size=12)
    sheet.row_dimensions[1].height = 10
    excel = root/'form.xlsx'
    book.save(excel)
    doc = Document()
    table = doc.add_table(rows=1, cols=1)
    table.rows[0].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    table.rows[0].height = Pt(8)
    paragraph = table.cell(0,0).paragraphs[0]
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    paragraph.paragraph_format.line_spacing = Pt(6)
    paragraph.paragraph_format.right_indent=Pt(-40)
    table.cell(0,0)._tc.get_or_add_tcPr().append(OxmlElement('w:noWrap'))
    paragraph.add_run('Начальное значение').font.size = Pt(12)
    bookmark(paragraph._p,0,len(paragraph.text),'BID_probe',10001)
    word = root/'form.docx'
    doc.save(word)
    for path, field in [
        (excel, dict(dest='A1', kind='text', prefix='', label='Текст', value='Начальное значение')),
        (word, dict(dest='BID_probe', kind='text', word=True, label='Текст',
                    value='Начальное значение', segments=[dict(bookmark='BID_probe',capacity=20,sample='Начальное значение')]))
    ]:
        mapping=root/(path.stem+path.suffix+'.json')
        mapping.write_text(json.dumps(dict(probe=field)),encoding='utf-8')
        output=root/(path.name+'.pdf')
        value=' '.join(f'Контроль{i:03d}' for i in range(20))
        process=subprocess.run(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass',
                                '-File',str(APP_DIR/'PreviewWorker.ps1'),'-WorkFile',str(path),
                                '-FieldMap',str(mapping)], input=json.dumps(dict(values=dict(probe=value),pdf=str(output)))+'\n',
                               capture_output=True,encoding='utf-8',timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        responses=[json.loads(line.lstrip('\ufeff')) for line in process.stdout.splitlines() if line.strip()]
        assert process.returncode==0,(process.stderr,responses)
        assert not any('error' in r for r in responses),responses
        with pymupdf.open(output) as pdf:
            printed=''.join(''.join(page.get_text().split()) for page in pdf)
        assert all(f'Контроль{i:03d}' in printed for i in range(20)),printed
        if path.suffix=='.xlsx':
            checked=load_workbook(path)
            assert checked.active.row_dimensions[1].height>10
            assert checked.active['A1'].font.sz==12
            assert not checked.active['A1'].alignment.shrinkToFit
            checked.close()
        else:
            checked=Document(path)
            assert checked.tables[0].rows[0].height_rule!=WD_ROW_HEIGHT_RULE.EXACTLY
        print('PASS',path.suffix,'all markers printed, height grows, font preserved')

    from word_fields import analyze_word
    for gap in (' ','  ','        ',' 12 ',None):
        document=Document()
        document.add_paragraph('АКТ освидетельствования скрытых работ')
        if gap is None:
            for value in ('Акт составлен в','','экземплярах'):document.add_paragraph(value)
        else:
            document.add_paragraph('Акт составлен в'+gap+'экземплярах')
        source=root/'copies.docx'
        document.save(source)
        prepared=root/'copies-prepared.docx'
        plan=analyze_word(source,prepared)
        assert plan['fields']['copies']['kind']=='number'
        mapping=root/'copies.json'
        mapping.write_text(json.dumps(plan['fields']),encoding='utf-8')
        requests=[]
        for index,value in enumerate(('12','','3')):
            requests.append(json.dumps(dict(values=dict(copies=value),pdf=str(root/f'copies-{index}.pdf'))))
        result=subprocess.run(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass',
                               '-File',str(APP_DIR/'PreviewWorker.ps1'),'-WorkFile',str(prepared),
                               '-FieldMap',str(mapping)],input='\n'.join(requests)+'\n',
                              capture_output=True,encoding='utf-8',timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        responses=[json.loads(line.lstrip('\ufeff')) for line in result.stdout.splitlines() if line.strip()]
        assert not any('error' in response for response in responses),responses
        if gap is not None:
            assert any('Акт составлен в 3 экземплярах' in p.text for p in Document(prepared).paragraphs)
        for index,value in enumerate(('12','','3')):
            with pymupdf.open(root/f'copies-{index}.pdf') as pdf:
                printed=''.join(''.join(page.get_text().split()) for page in pdf)
            assert 'Актсоставленв'+value+'экземплярах' in printed,printed
    print('PASS blank/spaced/filled copy count, clear and refill preserve the sentence')
