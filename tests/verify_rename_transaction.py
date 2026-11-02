"""Real Office: rename during an unsaved edit, warm reopen, project rollback."""
import tempfile,time,tkinter as tk,json
from pathlib import Path
from tkinter import ttk
from openpyxl import Workbook,load_workbook
from openpyxl.workbook.defined_name import DefinedName
import studio

def pump(root,until=lambda:False,timeout=.15):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        root.update();time.sleep(.01)
        if until():return True
    return until()

def children(w):
    for c in w.winfo_children():yield c;yield from children(c)

with tempfile.TemporaryDirectory() as td:
    p=Path(td);studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
    project=p/'project';base=project/'Документы';base.mkdir(parents=True)
    (project/'project.json').write_text('{}','utf-8')
    a=base/'A.xlsx';b=base/'B.xlsx';c=base/'Renamed.xlsx'
    book=Workbook();book.active['B2']='Original';book.defined_names.add(DefinedName('ID_User_test',attr_text="'Sheet'!$B$2"));book.save(a);book.save(b);book.close()
    original=a.read_bytes();manifest=(project/'project.json').read_bytes()
    root=tk.Tk();app=studio.Studio(root);errors=[]
    root.report_callback_exception=lambda *e:errors.append(str(e[1]))
    app.ensure_project_passports=lambda *a:None;app.enter(project)
    def ready(s):return s in app.latest and app.saved_rev.get(s,-1)==app.revisions.get(s)
    s=app.current;assert pump(root,lambda:ready(s),30),errors
    pid=s.thread
    app.views['ID_User_test'].set('Unsaved edit')
    app.perform_file_operation(a,'move',c)
    assert app.current is s and s.thread is pid and s.source==c and app.sessions[c] is s
    assert not a.exists() and c.read_bytes()==original and c in app.journal().dirty
    assert pump(root,lambda:ready(s),30),errors
    assert c.read_bytes()==original,'preview must not save the source file'
    app.open(b);assert app.decision.winfo_exists()
    next(w for w in children(app.decision) if isinstance(w,ttk.Button) and w.cget('text')=='Вернуться').invoke()
    assert app.current is s
    app.open(b)
    next(w for w in children(app.decision) if isinstance(w,ttk.Button) and w.cget('text')=='Сохранить').invoke()
    assert pump(root,lambda:app.current is not s,30),errors
    second=app.current;assert pump(root,lambda:ready(second),30),errors
    check=load_workbook(c);assert check.active['B2'].value=='Unsaved edit';check.close()
    # Clean documents remain open; switching back reuses the same Office worker.
    t=time.monotonic();app.open(c);pump(root)
    assert app.current is s and s.thread is pid and time.monotonic()-t<1
    assert app.needs_project_decision(),'document save must not erase the project opening baseline'
    app.close()
    next(w for w in children(app.decision) if isinstance(w,ttk.Button) and w.cget('text')=='Не сохранять').invoke()
    assert pump(root,lambda:a.exists() and not c.exists() and not s.thread.is_alive() and not second.thread.is_alive(),30),errors
    assert a.read_bytes()==original and not c.exists()
    assert (project/'project.json').read_bytes()==manifest
    assert not errors,errors
    print('PASS unsaved rename preserves session/source bytes/prompt; explicit save; warm switch; full opening-state project rollback')
