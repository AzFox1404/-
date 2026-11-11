"""Alternate register columns keep formulas and numbering through edits."""
import queue
import tempfile
from pathlib import Path
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Border, Side
from workspace_preview import Session
from verify_form_corpus import wait_for

with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'register.xlsx'
    workbook=Workbook()
    sheet=workbook.active
    for coordinate,value in {'A6':'№ п/п','B6':'Наименование документа','C6':'Номер документа',
                             'F6':'Количество листов','G6':'Страница по списку',
                             'A12':'Сдал','A14':'Принял'}.items():
        sheet[coordinate]=value
    border=Border(bottom=Side(style='thin'))
    for row in range(7,11):
        sheet.cell(row,1,row-6)
        sheet.cell(row,2,'Документ')
        sheet.cell(row,6,2)
        sheet.cell(row,7,1 if row==7 else f'=G{row-1}+F{row-1}')
        for col in range(1,8):sheet.cell(row,col).border=border
    workbook.save(path)
    session=Session(path,queue.Queue(),prepared=True)
    try:
        wait_for(session,'fields');wait_for(session,'pdf')
        for revision,operation in enumerate([
            dict(row=7,rows=[7],count=2,delete=False,after=True),
            dict(row=7,rows=[8,9],delete=True)
        ],1):
            session.tasks.put(dict(revision=revision,**operation))
            wait_for(session,'rows');wait_for(session,'pdf')
            assert not session.formula_errors,session.formula_errors
        checked=load_workbook(path,data_only=True)
        sheet=checked.active
        assert [sheet.cell(r,1).value for r in range(7,11)]==[1,2,3,4]
        assert [sheet.cell(r,7).value for r in range(7,11)]==[1,3,5,7]
        assert any(c[0].value=='Сдал' for c in sheet)
        checked.close()
        print('PASS alternate columns, insertion/deletion, page counts and signatures')
    finally:
        session.tasks.put(None);session.thread.join(35)
        assert not session.thread.is_alive()
