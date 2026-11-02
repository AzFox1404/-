"""Word uses the same isolated source and explicit project save contract."""
import tempfile,time,tkinter as tk
from pathlib import Path
from tkinter import ttk
from docx import Document
import studio

def pump(root,until,timeout=40):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        root.update();time.sleep(.01)
        if until():return True
    return False

def children(w):
    for c in w.winfo_children():yield c;yield from children(c)

with tempfile.TemporaryDirectory() as td:
    p=Path(td);studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
    project=p/'project';base=project/'Документы';base.mkdir(parents=True);(project/'project.json').write_text('{}')
    source=base/'Титул.docx';target=base/'Новый титул.docx'
    doc=Document();doc.add_paragraph('ИСПОЛНИТЕЛЬНАЯ ДОКУМЕНТАЦИЯ');doc.add_paragraph('Объект: Исходное');doc.save(source);original=source.read_bytes()
    root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]))
    app.ensure_project_passports=lambda *a:None;app.enter(project);s=app.current
    def ready():return s in app.latest and app.saved_rev.get(s,-1)==app.revisions.get(s)
    assert pump(root,ready),errors
    app.views['titleAddress'].set('Новый объект');app.perform_file_operation(source,'move',target)
    assert pump(root,ready),errors
    assert target.read_bytes()==original and s.source==target
    # Discarding the document restores its name as well as its content.
    app.close_document()
    next(w for w in children(app.decision) if isinstance(w,ttk.Button) and w.cget('text')=='Не сохранять').invoke()
    assert pump(root,lambda:app.current is None and not app.stopping),errors
    assert source.read_bytes()==original and not target.exists()
    app.open(source);s=app.current;assert pump(root,ready),errors
    app.perform_file_operation(source,'move',target)
    app.views['titleAddress'].set('Сохранённый объект');assert pump(root,ready),errors
    app.close()
    next(w for w in children(app.decision) if isinstance(w,ttk.Button) and w.cget('text')=='Сохранить').invoke()
    assert pump(root,lambda:not (project/'.recovery').exists() and not s.thread.is_alive()),errors
    assert not source.exists() and 'Сохранённый объект' in '\n'.join(x.text for x in Document(target).paragraphs)
    assert not errors,errors
    print('PASS Word preview never saves source on rename; document discard; explicit whole-project save publishes final name and content')
