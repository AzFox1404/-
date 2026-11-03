from test_pdf_wait import wait_pdf
import tempfile,time,tkinter as tk
from pathlib import Path
from tkinter import ttk
from reportlab.pdfgen import canvas
from pypdf import PdfReader
import studio,scanner_ui
from pdf_page_preview import PagePreview

def widgets(w):
 for c in w.winfo_children():yield c;yield from widgets(c)
def pump(root,seconds=.2):
 end=time.monotonic()+seconds
 while time.monotonic()<end:root.update();time.sleep(.01)
with tempfile.TemporaryDirectory() as td:
 folder=Path(td);pdf=folder/'two-certificates.pdf';c=canvas.Canvas(str(pdf),pagesize=(450,600))
 for n in range(4):c.drawString(50,550,f'PAGE {n+1}');c.showPage()
 c.save()
 studio.STORE=folder/'s';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[];dialogs=[];saved=[]
 root.report_callback_exception=lambda *e:errors.append(str(e[1]))
 records=[dict(path=str(pdf),source=pdf.name,start=a,end=b,type='Сертификат качества',number=num,date='14.01.2024',material='Двутавр',pages=['']*4) for a,b,num in ((1,2,'100539'),(3,4,'869'))]
 scanner_ui.inspect=lambda *args:records
 scanner_ui.messagebox.showerror=lambda *args,**kw:dialogs.append(args)
 scanner_ui.messagebox.showinfo=lambda *args,**kw:None
 scanner_ui.messagebox.askyesno=lambda *args,**kw:True
 app.store_passports=lambda folder,meta:saved.append((folder,meta))
 scanner_ui.scanner(app,files=[pdf],destination=folder/'output');pump(root,.6)
 win=app.active_scan;preview=next(w for w in widgets(win) if isinstance(w,PagePreview));lb=next(w for w in widgets(win) if isinstance(w,tk.Listbox))
 from types import SimpleNamespace
 def invoke_icon(widget):
  widget.event_generate('<ButtonPress-1>',x=10,y=10);widget.event_generate('<ButtonRelease-1>',x=10,y=10)
 aliases={'Разделить перед текущей страницей':'Разделить с текущей страницы','Сохранить отмеченные документы отдельными PDF':'Подтвердить и сохранить'}
 buttons={aliases.get(w.hint_message,w.hint_message):SimpleNamespace(invoke=lambda item=w:invoke_icon(item)) for w in widgets(win) if isinstance(getattr(w,'hint_message',None),str)}
 wait_pdf(root,preview)
 split=buttons['Разделить с текущей страницы'];preview.set_zoom(120);pump(root)
 # Exact screenshot: record 3-4, currently on its first page 3.
 lb.selection_clear(0,'end');lb.selection_set(1);lb.event_generate('<<ListboxSelect>>');pump(root)
 assert preview.number==2
 split.invoke();pump(root)
 assert not dialogs,dialogs
 assert [(r['start'],r['end']) for r in records]==[(1,2),(3,4)]
 assert records[1]['number']=='869' and list(lb.curselection())==[1]
 # Continuous scroll into another record must split that record, without overlaps.
 lb.selection_clear(0,'end');lb.selection_set(0);lb.event_generate('<<ListboxSelect>>');pump(root)
 preview.go_to(3);pump(root);assert preview.number==3
 split.invoke();pump(root)
 assert [(r['start'],r['end']) for r in records]==[(1,2),(3,3),(4,4)]
 assert records[1]['number']=='869' and records[2]['number']==''
 split.invoke();pump(root);assert len(records)==3 and not dialogs
 buttons['Подтвердить и сохранить'].invoke();pump(root)
 assert not dialogs,dialogs
 end=time.monotonic()+10
 while not saved and time.monotonic()<end:pump(root,.05)
 assert saved and len(saved[0][1])==3
 output,meta=saved[0]
 assert [len(PdfReader(output/r['file']).pages) for r in meta]==[2,1,1]
 assert sum(len(PdfReader(output/r['file']).pages) for r in meta)==4
 assert not errors,errors
 app.close()
 print('PASS existing boundary is harmless; cross-record scroll split; repeat click; saved 2+1+1 pages without loss/duplication',flush=True)
