"""Known empty forms retain editable slots without sample values or row numbers."""
import json
import queue
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from docx.shared import Pt
from openpyxl import Workbook
from openpyxl.styles import Border, Side

from app_paths import APP_DIR
from office_forms import extra_fields
from word_fields import analyze_word
from workspace_preview import Session
from verify_form_corpus import wait_for

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    order = Document()
    for text in ['Общество с ограниченной ответственностью', '', '', 'Приказ № ', 'г.',
                 'На Объекте: , расположенное по адресу: .', 'ПРИКАЗЫВАЮ:',
                 'Назначить , производителя работ \n , ответственным за работы.',
                 'Генеральный директор     ', 'С приказом ознакомлен:', 'Производитель работ     ']:
        order.add_paragraph(text)
    path = root/'order.docx'
    order.save(path)
    fields = analyze_word(path)['fields']
    assert {'orderIssuer','orderRequisites','orderNumber','orderDate','orderObject','orderAddress',
            'orderAppointee','orderEmployer','orderDirector','orderAcknowledged'} <= fields.keys()
    assert not any(field['value'] for field in fields.values()), fields

    appendix = Document()
    for text in ['Приложение №', 'к Акту  от    освидетельствования скрытых работ   по адресу: ',
                 'Реестр документов качества № ']:
        appendix.add_paragraph(text)
    path = root/'appendix.docx'
    appendix.save(path)
    assert {'appendixNumber','actRef','refDate','refWork','regAddress','qualityNumber'} <= analyze_word(path)['fields'].keys()

    act = Document()
    for text in ['АКТ освидетельствования ответственных конструкций', '№', '', '«', '', '»', '', '', '20', 'г.']:
        act.add_paragraph(text)
    source = root/'act.docx'
    prepared = root/'prepared.docx'
    act.paragraphs[2].add_run('').font.size = Pt(1)
    act.save(source)
    fields = analyze_word(source,prepared)['fields']
    assert fields['actDate']['value'] == '' and len(fields['actDate']['segments']) == 3
    fields['number']['segments'][0]['fontSize'] = 12
    mapping = root/'fields.json'
    mapping.write_text(json.dumps(fields),encoding='utf-8')
    requests = '\n'.join(json.dumps(dict(values=dict(actDate=value,number='Readable'),pdf=str(root/f'date-{i}.pdf')))
                         for i,value in enumerate(('03.05.2027','','04.06.2028')))+'\n'
    response = subprocess.run(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',
                               str(APP_DIR/'PreviewWorker.ps1'),'-WorkFile',str(prepared),'-FieldMap',str(mapping)],
                              input=requests,capture_output=True,encoding='utf-8',timeout=120,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    messages = [json.loads(line.lstrip('\ufeff')) for line in response.stdout.splitlines() if line.strip()]
    assert response.returncode == 0 and not any('error' in item for item in messages), (response.stderr,messages)
    printed = [p.text for p in Document(prepared).paragraphs]
    assert all(run.font.size == Pt(12) for paragraph in Document(prepared).paragraphs if paragraph.text == 'Readable' for run in paragraph.runs if run.text)
    assert '04' in printed and 'июня' in printed and '2028' in printed, printed

    workbook = Workbook()
    sheet = workbook.active
    for coordinate,value in {'B8':'Материал','C8':'Вид документа','D8':'Номер документа','E8':'Дата',
                             'F8':'Количество листов','B12':'Всего страниц:'}.items():
        sheet[coordinate] = value
    for row in range(9,12):
        for column in range(1,7):
            sheet.cell(row,column).border = Border(bottom=Side(style='thin'))
    path = root/'quality.xlsx'
    workbook.save(path)
    fields = extra_fields(path)
    assert len([key for key in fields if key.startswith('row')]) == 15, fields

    registry = Document()
    registry.add_paragraph('Реестр документов качества № ')
    table = registry.add_table(rows=3,cols=5)
    for cell,label in zip(table.rows[0].cells,['№ п/п','Материал','Документ подтверждающий качество','Номер документа','Дата']):
        cell.text = label
    path = root/'registry.docx'
    registry.save(path)
    session = Session(path,queue.Queue(),prepared=True)
    try:
        wait_for(session,'fields'); wait_for(session,'pdf')
        for revision,operation in enumerate([dict(row=2,rows=[2],count=1,after=True,delete=False),
                                              dict(row=2,rows=[3],delete=True)],1):
            session.tasks.put(dict(revision=revision,**operation))
            wait_for(session,'rows'); wait_for(session,'pdf')
        saved = Document(path).tables[0]
        assert len(saved.rows) == 3
        assert [row.cells[0].text for row in saved.rows[1:]] == ['1','2']
    finally:
        session.tasks.put(None); session.thread.join(35)
        assert not session.thread.is_alive()

print('PASS empty orders, appendix headers, split dates through Office and unnumbered register rows')
