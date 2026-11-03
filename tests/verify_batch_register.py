"""Office regression using generated forms, never user documents."""
import queue,tempfile
from pathlib import Path
from openpyxl import Workbook,load_workbook
from workspace_preview import Session

def wait(s,kind):
    while True:
        _,event,payload=s.events.get(timeout=120)
        if event=='error':raise AssertionError(payload)
        if event==kind:return payload

with tempfile.TemporaryDirectory() as td:
    path=Path(td)/'Реестр.xlsx';w=Workbook();ws=w.active
    ws['A5']='РЕЕСТР ИСПОЛНИТЕЛЬНОЙ ДОКУМЕНТАЦИИ'
    for r,title in [(8,'Раздел первый'),(14,'Раздел второй')]:
        ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=6);ws.cell(r,1,title)
    for r in [9,10,11,12,15,16]:
        ws.cell(r,1,r);ws.cell(r,2,'Документ '+str(r));ws.cell(r,5,2)
    ws['A19']='Передал';ws['A21']='Принял';w.save(path);w.close()
    s=Session(path,queue.Queue(),prepared=True)
    try:
        wait(s,'fields');wait(s,'pdf')
        for revision,operation in enumerate([
            dict(row=9,rows=[9,11],delete=True),
            dict(row=9,rows=[9],count=3,delete=False),
            dict(row=9,section=8,title='Новый раздел',delete=False),
            dict(row=9,section=8,delete=True),
        ],1):
            s.tasks.put(dict(revision=revision,**operation));fields,selected=wait(s,'rows');wait(s,'pdf')
            book=load_workbook(path,data_only=True);sheet=book.active
            names=[sheet.cell(r,2).value for r in range(1,sheet.max_row+1)]
            if revision==1:
                assert 'Документ 9' not in names and 'Документ 11' not in names
                assert 'Документ 10' in names and 'Документ 12' in names
            if revision==2:assert len({k.split('_')[0] for k in fields if k.startswith('row')})==7
            if revision==3:assert 'Новый раздел' in [c[0].value for c in sheet]
            if revision==4:
                headings=[c[0].value for c in sheet]
                assert 'Раздел первый' not in headings and 'Новый раздел' in headings and 'Раздел второй' in headings
                assert 'Передал' in headings and 'Принял' in headings
            assert not s.formula_errors,s.formula_errors
            book.close()
        print('PASS batch noncontiguous delete, multi-insert, section clone/delete, formulas and signatures')
    finally:
        s.tasks.put(None);s.thread.join(30)

    # Exercise the real filling toolbar at its minimum and floating width.
    import tkinter as tk
    import time
    import studio
    studio.STORE=Path(td)/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
    root=tk.Tk();app=studio.Studio(root);errors=[]
    root.report_callback_exception=lambda *e:errors.append(str(e[1]))
    app.import_item('file',path)
    end=time.monotonic()+90
    while time.monotonic()<end and app.current not in getattr(app,'latest',{}):root.update();time.sleep(.02)
    assert app.current in app.latest,errors
    def check():
        host=app.windows.get(1,app.holders[1])
        bars=[w for w in host.winfo_children() if getattr(w,'panel_toolbar',False)]
        assert len(bars)==2,len(bars)
        for bar in bars:
            for button in bar.winfo_children():
                assert button.winfo_x()>=0 and button.winfo_x()+button.winfo_width()<=bar.winfo_width()
                assert button.has_hint
    root.update();app.enforce_panel_sizes();root.update();check()
    app.detach(1);root.update();app.windows[1].geometry('180x500');app.enforce_panel_sizes();root.update();check()
    app.dock(1);root.update()
    for worker in app.sessions.values():worker.tasks.put(None)
    for worker in app.sessions.values():worker.thread.join(30)
    root.destroy();assert not errors,errors
    print('PASS registry toolbar icons and hints fit docked and minimum floating filling panel')
