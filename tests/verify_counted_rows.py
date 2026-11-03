"""Generated Excel only: insertion after first row and bounded deletion."""
import queue,tempfile
from pathlib import Path
from openpyxl import Workbook,load_workbook
from workspace_preview import Session
from register_selection import following_rows

def wait(s,kind):
    while True:
        _,event,data=s.events.get(timeout=120)
        if event=='error':raise AssertionError(data)
        if event==kind:return data

values={'part8':'КЖ','group9':'АОСР','row10_2':'Акт','row11_2':'Акт 2',
        'row12_2':'Акт 3','group13':'Паспорта','row14_2':'Паспорт','part15':'КМ','row16_2':'Акт'}
assert following_rows(values,10,999)==([11,12],2)
assert following_rows(values,12,1)==([],0)
assert following_rows({'row2_2':'A','row3_2':'B','row5_2':'C'},2,99)==([3],1)

with tempfile.TemporaryDirectory() as td:
    path=Path(td)/'Реестр.xlsx';w=Workbook();ws=w.active
    ws['A5']='РЕЕСТР ИСПОЛНИТЕЛЬНОЙ ДОКУМЕНТАЦИИ'
    for r,title in [(8,'КЖ'),(12,'Паспорта'),(15,'КМ')]:
        ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=6);ws.cell(r,1,title)
    for i,r in enumerate([9,10,11,13,14,16],1):
        ws.cell(r,1,i);ws.cell(r,2,'Документ '+str(r));ws.cell(r,5,2)
    ws['A19']='Передал';w.save(path);w.close()
    s=Session(path,queue.Queue(),prepared=True)
    try:
        wait(s,'fields');wait(s,'pdf')
        s.tasks.put(dict(row=9,rows=[9],count=2,after=True,delete=False,revision=1))
        fields,selected=wait(s,'rows');wait(s,'pdf')
        assert selected==11,selected
        w=load_workbook(path,data_only=True);ws=w.active
        assert ws['B9'].value=='Документ 9'
        assert ws['B10'].value is None and ws['B11'].value is None
        assert ws['B12'].value=='Документ 10';w.close()
        targets,available=following_rows(fields,9,999)
        assert targets==[10,11,12,13],targets
        s.tasks.put(dict(row=9,rows=targets,delete=True,revision=2,notice='Удалено строк: 4'))
        fields,selected=wait(s,'rows');assert wait(s,'notice')=='Удалено строк: 4';wait(s,'pdf')
        w=load_workbook(path,data_only=True);ws=w.active
        assert ws['B9'].value=='Документ 9'
        assert ws['A10'].value=='Паспорта'
        assert ws['B11'].value=='Документ 13'
        assert ws['A13'].value=='КМ' and ws['B14'].value=='Документ 16'
        assert [ws.cell(r,1).value for r in (9,11,12,14)]==[1,2,3,1]
        assert [ws.cell(r,6).value for r in (9,11,12,14)]==[1,3,5,7]
        assert not s.formula_errors,s.formula_errors
        w.close()
    finally:s.tasks.put(None);s.thread.join(30)
print('PASS counted insertion after first, delete capped before heading, unchanged neighbours, formulas and completion notice')

# Word has separate row logic: confirm the new after flag there as well.
from docx import Document
with tempfile.TemporaryDirectory() as td:
    path=Path(td)/'Приложение.docx';d=Document();d.add_paragraph('Реестр документов качества №1')
    table=d.add_table(rows=1,cols=5)
    for cell,label in zip(table.rows[0].cells,['№ п/п','Наименование документа','Номер документа','Дата','Количество листов']):cell.text=label
    for i in range(1,4):
        for cell,value in zip(table.add_row().cells,[str(i),'Документ '+str(i),str(i),'01.01.2026','2']):cell.text=value
    d.save(path);s=Session(path,queue.Queue(),prepared=True)
    try:
        wait(s,'fields');wait(s,'pdf')
        s.tasks.put(dict(row=2,rows=[2],count=2,after=True,delete=False,revision=1))
        fields,selected=wait(s,'rows');wait(s,'pdf')
        rows=Document(path).tables[0].rows
        assert rows[1].cells[1].text=='Документ 1'
        assert rows[2].cells[1].text=='' and rows[3].cells[1].text==''
        assert rows[4].cells[1].text=='Документ 2'
        s.tasks.put(dict(row=2,rows=[3,4,5],delete=True,revision=2))
        wait(s,'rows');wait(s,'pdf')
        rows=Document(path).tables[0].rows
        assert [r.cells[0].text for r in rows[1:]]==['1','2']
        assert [r.cells[1].text for r in rows[1:]]==['Документ 1','Документ 3']
        assert not s.formula_errors,s.formula_errors
    finally:s.tasks.put(None);s.thread.join(30)
print('PASS separate Word insertion-after, batch deletion, ordinal rebuild and column preservation')
