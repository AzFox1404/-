"""Open a real temporary project; auto analyse passports without mocks."""
import hashlib,json,tempfile,time,tkinter as tk
from pathlib import Path
from reportlab.pdfgen import canvas
from pdf_page_preview import PagePreview
import studio

def descendants(w):
    for child in w.winfo_children():yield child;yield from descendants(child)

with tempfile.TemporaryDirectory() as td:
    p=Path(td);studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Projects';studio.LIB=studio.STORE/'Library';studio.SAMPLES=p/'absent/sample'
    project=studio.PROJECTS/'Test';folder=project/'Документы/Паспорта';folder.mkdir(parents=True)
    (project/'project.json').write_text('{}','utf-8')
    pdf=folder/'Паспорт.pdf';c=canvas.Canvas(str(pdf))
    for i in range(3):c.drawString(40,700,'Sample passport native text, enough characters to skip OCR, page '+str(i));c.showPage()
    c.save();original=hashlib.sha256(pdf.read_bytes()).hexdigest()
    root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]))
    pulses=[]
    def beat():
        pulses.append(time.monotonic());root.after(40,beat)
    beat();app.enter(project)
    for attempt in range(3):
        if attempt:app.ensure_project_passports(project,force=True)
        end=time.monotonic()+20;preview=None
        while time.monotonic()<end:
            root.update();time.sleep(.005)
            win=getattr(app,'active_scan',None)
            if win and win.winfo_exists():
                preview=next((w for w in descendants(win) if isinstance(w,PagePreview)),None)
                if preview and preview.selection.pages:break
        assert preview and preview.selection.pages,errors
        assert len([w for w in descendants(win) if getattr(w,'hint_message','')=='Разделить перед текущей страницей'])==1
        win.tk.call(win.protocol('WM_DELETE_WINDOW'))
        for _ in range(15):root.update();time.sleep(.005)
    assert len(pulses)>10 and max(b-a for a,b in zip(pulses,pulses[1:]))<2,'Tk blocked during scanner analysis'
    assert hashlib.sha256(pdf.read_bytes()).hexdigest()==original
    assert not errors,errors
    app.project=None;app.close()
print('PASS project open -> automatic real analysis -> rendered preview, repeat 3x, responsive Tk and untouched source')
