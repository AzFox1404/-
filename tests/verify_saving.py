import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk
import studio
import traceback
from workspace_preview import SAMPLES
from openpyxl import load_workbook

def descendants(w):
    for child in w.winfo_children():
        yield child
        yield from descendants(child)

with tempfile.TemporaryDirectory() as td:
    studio.STORE=Path(td)/'store'
    studio.PROJECTS=studio.STORE/'Проекты'
    studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
    root=tk.Tk()
    app=studio.Studio(root)
    errors=[]
    root.report_callback_exception=lambda *e:(errors.append(e[1]),traceback.print_exception(*e),root.destroy())
    app.import_item('file',next((SAMPLES.parent/'Шаблоны').glob('*АОСР*')))
    file=app.current.source
    baseline=app.journal().copies[file.relative_to(app.project/'Документы')].read_bytes()
    def wait(fn):
        if app.current and app.current in app.latest and app.saved_rev.get(app.current,-1)==app.revisions[app.current]:
            fn()
        else:root.after(150,lambda:wait(fn))
    def edited():
        app.views['nextWork'].set('Проверка продолжения поля '*25)
        root.after(900,lambda:wait(verify))
    def choose(label):
        next(b for b in descendants(app.decision) if isinstance(b,ttk.Button) and b.cget('text')==label).invoke()
    def verify():
        wb=load_workbook(file)
        sheet=wb.active
        refs=[list(wb.defined_names[n].destinations)[0][1].replace('$','').split(':')[0] for n in wb.defined_names if n.startswith('BID_more_nextWork')]
        caption=next(c.row for row in sheet for c in row if str(c.value or '').startswith('(наименование работ, конструкций'))
        print('ROWS',caption,[(c,sheet[c].row,sheet[c].font.u,sheet[c].border.bottom.style) for c in refs],flush=True)
        assert refs and all(sheet[c].row<caption and sheet[c].font.u is None and
                           (sheet[c].border.bottom.style or sheet.cell(sheet[c].row+1,2).border.top.style)
                           for c in refs)
        assert sheet['G67'].font.u is None
        app.close_document()
        assert app.decision.grab_current()==app.decision
        app.decision.tk.eval(app.decision.protocol('WM_DELETE_WINDOW'))
        assert app.current is not None
        app.close_document()
        choose('Не сохранять')
        root.after(200,restored)
    def restored():
        if app.current is not None:root.after(150,restored);return
        assert file.read_bytes()==baseline
        print('PASS exact restore, cancel, underline, caption position',flush=True)
        app.open(file)
        root.after(150,lambda:wait(edit_save))
    def edit_save():
        app.views['nextWork'].set('Монтаж стен')
        root.after(900,lambda:wait(save))
    def save():
        app.close_document()
        choose('Сохранить')
        root.after(150,saved)
    def saved():
        if app.current is not None:root.after(150,saved);return
        assert load_workbook(file).active['G67'].value=='Монтаж стен'
        assert not app.journal().dirty_project()
        print('PASS save commits last edit',flush=True)
        app.close()
    root.after(150,lambda:wait(edited))
    root.after(100000,root.destroy)
    root.mainloop()
    assert not errors,errors
