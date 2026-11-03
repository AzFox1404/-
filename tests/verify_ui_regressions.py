"""Real filling controls, accelerated scroll and window restore; generated data only."""
import tempfile,time,queue,tkinter as tk
from tkinter import ttk
from pathlib import Path
from docx import Document
import studio
from word_fields import analyze_word
from smooth_scrollbar import Scrollbar

def pump(root,seconds=.08):
    end=time.monotonic()+seconds
    while time.monotonic()<end:root.update();time.sleep(.004)

with tempfile.TemporaryDirectory() as td:
    p=Path(td);studio.STORE=p/'store';studio.PROJECTS=p/'projects';studio.LIB=p/'library';studio.SAMPLES=p/'absent/sample'
    root=tk.Tk();app=studio.Studio(root);errors=[]
    def report(*e):errors.append(str(e[1]));__import__('traceback').print_exception(*e)
    root.report_callback_exception=report
    project=p/'project';project.mkdir();(project/'Документы').mkdir();(project/'project.json').write_text('{}')
    class S:pass
    s=S();s.source=project/'Документы/sample.docx';s.source.write_bytes(b'untouched');s.labels={f'field{i}':f'Поле {i}' for i in range(100)};s.spec={};s.preview_context={};s.tasks=queue.Queue()
    app.project=project;app.current=s;app.models={s:{k:'' for k in s.labels}};app.pending={};app.revisions={s:0};app.manual=set();app.views={};app.status=tk.StringVar()
    top=tk.Toplevel(root);top.geometry('720x620');body=tk.Frame(top);body.pack(fill='both',expand=True);app.body={1:body};app.form();pump(root)
    entry=next(w for w in body.winfo_children() if isinstance(w,tk.Canvas))
    def descend(w):
        for c in w.winfo_children():yield c;yield from descend(c)
    field=next(w for w in descend(body) if isinstance(w,ttk.Combobox));field.focus_force();pump(root)
    app.views['field0'].set('Первый текст');app.views['field0'].set('Новый текст')
    def key(code,state=4):field.event_generate('<KeyPress>',keycode=code,state=state);pump(root,.02)
    key(90);assert field.get()=='Первый текст',field.get()
    key(89);assert field.get()=='Новый текст'
    key(65);key(67);assert root.clipboard_get()=='Новый текст'
    key(88);assert field.get()==''
    key(86);assert field.get()=='Новый текст'
    key(65);root.clipboard_clear();root.clipboard_append('Замена');key(86);assert field.get()=='Замена'
    key(90);assert field.get()=='Новый текст','paste must be one undo step'
    key(90,5);assert field.get()=='Замена','Ctrl+Shift+Z redo'
    canvas=app.form_canvas
    for _ in range(15):canvas.yview_scroll(10,'units');pump(root,.02)
    assert canvas.yview()[0]>0 and canvas.repaint_installed
    for _ in range(15):canvas.yview_scroll(-10,'units');pump(root,.02)
    assert canvas.yview()[0]==0 and field.get()=='Замена'
    bars=[w for w in descend(body) if isinstance(w,Scrollbar)];assert bars and bars[0].winfo_width()<=14
    bar=bars[0];bar.event_generate('<Enter>');pump(root,.2);assert bar.hot==1
    bar.event_generate('<Leave>');pump(root,.2);assert bar.hot==0
    geometry=top.geometry();app.windows={1:top};app.maximize(top);pump(root);assert top.attributes('-fullscreen') and top._bottom_safe.winfo_height()>=24
    app.maximize(top);pump(root);assert not top.attributes('-fullscreen')
    assert top.geometry()==geometry,(top.geometry(),geometry)
    docked=[];original_dock=app.dock;app.dock=lambda n:docked.append(n)
    top._maximize_from_dock=True;app.maximize(top);pump(root);app.maximize(top);pump(root)
    assert docked==[1],'maximized docked pane must return to its original pane'
    top._maximize_from_dock=False;app.maximize(top);app.dock=original_dock
    # Colon is a caption, not a replaceable value.
    d=Document();d.add_paragraph('АКТ освидетельствования скрытых работ');d.add_paragraph('Дополнительные сведения:');d.add_paragraph().add_run('').underline=True;d.add_paragraph('Акт составлен в 3 экземплярах')
    source=p/'notes.docx';d.save(source);before=source.read_bytes();plan=analyze_word(source,p/'prepared.docx')
    assert plan['fields']['notes']['value']=='',plan['fields']['notes']
    assert Document(p/'prepared.docx').paragraphs[1].text=='Дополнительные сведения:' and source.read_bytes()==before
    for job in list(app.pending.values()):root.after_cancel(job)
    app.pending.clear();root.destroy();assert not errors,errors
print('PASS real form Ctrl+C/V/X/A/Z/Y/Shift+Z, atomic paste undo, scroll repaint/value preservation, animated rounded scrollbar, fullscreen restore and protected notes colon')
