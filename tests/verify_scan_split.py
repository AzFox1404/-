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
 # The second card shows only source pages 3-4, numbered locally 1-2.
 lb.selection_clear(0,'end');lb.selection_set(1);lb.event_generate('<<ListboxSelect>>');pump(root)
 wait_pdf(root,preview)
 assert preview.number==0 and len(preview.pages)==2 and preview.page_range==(2,4)
 split.invoke();pump(root)
 assert not dialogs,dialogs
 assert [(r['start'],r['end']) for r in records]==[(1,2),(3,4)]
 assert records[1]['number']=='869' and list(lb.curselection())==[1]
 # Scrolling to the end cannot expose pages assigned to the other card.
 lb.selection_clear(0,'end');lb.selection_set(0);lb.event_generate('<<ListboxSelect>>');pump(root)
 wait_pdf(root,preview)
 preview.go_to(99);pump(root);assert preview.number==1 and len(preview.pages)==2
 lb.selection_clear(0,'end');lb.selection_set(1);lb.event_generate('<<ListboxSelect>>');pump(root)
 wait_pdf(root,preview)
 preview.go_to(1);pump(root)
 # Rotation uses the original source page even though the preview index is local.
 preview.rotate(90);pump(root)
 split.invoke();pump(root)
 assert [(r['start'],r['end']) for r in records]==[(1,2),(3,3),(4,4)]
 assert records[1]['number']=='869' and records[2]['number']==''
 wait_pdf(root,preview)
 assert lb.curselection()==(1,) and len(preview.pages)==1 and preview.page_range==(2,3)
 # Recombine and split again: preview geometry must follow both operations.
 buttons['Объединить со следующим документом'].invoke();pump(root);wait_pdf(root,preview)
 assert [(r['start'],r['end']) for r in records]==[(1,2),(3,4)] and len(preview.pages)==2
 preview.go_to(1);pump(root);split.invoke();pump(root);wait_pdf(root,preview)
 assert len(preview.pages)==1 and preview.page_range==(2,3)
 split.invoke();pump(root);assert len(records)==3 and not dialogs
 lb.selection_clear(0,'end');lb.selection_set(2);lb.event_generate('<<ListboxSelect>>');pump(root);wait_pdf(root,preview)
 assert preview.page_range==(3,4) and preview.selection.page_offset==3 and preview.rotations.get('0')==90
 assert preview.pages[0][1]>preview.pages[0][2]
 buttons['Подтвердить и сохранить'].invoke();pump(root)
 assert not dialogs,dialogs
 end=time.monotonic()+10
 while not saved and time.monotonic()<end:pump(root,.05)
 assert saved and len(saved[0][1])==3
 output,meta=saved[0]
 assert [len(PdfReader(output/r['file']).pages) for r in meta]==[2,1,1]
 assert sum(len(PdfReader(output/r['file']).pages) for r in meta)==4
 assert [PdfReader(output/r['file']).pages[0].rotation for r in meta]==[0,0,90]
 assert not errors,errors
 app.close()
 print('PASS record-only preview, split/merge geometry, repeat click; saved 2+1+1 pages without loss/duplication',flush=True)
