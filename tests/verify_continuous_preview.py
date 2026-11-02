from test_pdf_wait import wait_pdf
import tempfile,time,tkinter as tk
from pathlib import Path
from reportlab.pdfgen import canvas
from tkinter import ttk
import studio,scanner_ui
from pdf_page_preview import PagePreview

def widgets(w):
 for c in w.winfo_children():
  yield c;yield from widgets(c)
def pump(root,seconds=.25):
 end=time.monotonic()+seconds
 while time.monotonic()<end:root.update();time.sleep(.015)
with tempfile.TemporaryDirectory() as td:
 folder=Path(td);pdf=folder/'pages.pdf';c=canvas.Canvas(str(pdf),pagesize=(450,600))
 for n in range(30):
  c.setFont('Helvetica',32);c.drawString(60,510,f'PAGE {n+1}');c.rect(30,30,390,540);c.showPage()
 c.save()
 studio.STORE=folder/'s';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[]
 root.report_callback_exception=lambda *e:errors.append(str(e[1]))
 scanner_ui.inspect=lambda *args:[dict(path=str(pdf),source='Паспорт с длинным названием.pdf',start=1,end=30,type='Паспорт качества',number=str(i),date='',material='',pages=[{}]*30) for i in range(20)]
 scanner_ui.scanner(app,files=[pdf]);pump(root,.7)
 win=app.active_scan;preview=next(w for w in widgets(win) if isinstance(w,PagePreview));lb=next(w for w in widgets(win) if isinstance(w,tk.Listbox))
 win.geometry('1050x680');pump(root);small=lb.winfo_height()
 win.geometry('1500x950');pump(root);large=lb.winfo_height()
 assert large>small+200,(small,large)
 assert lb.winfo_width()>400
 wait_pdf(root,preview);preview.set_zoom(50);pump(root)
 assert len(preview.pages)==30 and preview.pages[1][0]>preview.pages[0][0]+preview.pages[0][2]
 assert len(preview.images)<6,len(preview.images)
 first=preview.canvas.yview()
 for _ in range(9):preview.canvas.event_generate('<MouseWheel>',delta=-120);pump(root,.02)
 assert preview.canvas.yview()[0]>first[0] and preview.number>0,(preview.canvas.yview(),preview.number)
 page=preview.number;preview.rotate(-90);pump(root)
 assert preview.rotations[str(page)]==270
 preview.rotate(90);pump(root);assert preview.rotations[str(page)]==0
 preview.go_to(20);pump(root);assert preview.number==20,preview.number
 for _ in range(5):preview.canvas.event_generate('<MouseWheel>',delta=120);pump(root,.02)
 assert preview.number<20
 before=preview.zoom;preview.canvas.event_generate('<Control-MouseWheel>',delta=120);pump(root)
 assert preview.zoom==before+10
 assert len(preview.images)<6
 # Moving to another document starts at its first assigned page.
 preview.show(pdf,8,{});pump(root);assert preview.number==8,preview.number
 preview.show(pdf,0,{});pump(root)
 from PIL import ImageGrab
 Path('review').mkdir(exist_ok=True);win.lift();pump(root)
 x,y=win.winfo_rootx(),win.winfo_rooty()
 ImageGrab.grab((x,y,x+win.winfo_width(),y+win.winfo_height())).save('review/scanner-continuous.png')
 assert not errors,errors
 win.tk.call(win.protocol('WM_DELETE_WINDOW'));app.close()
 print(f'PASS continuous 30-page PDF, wheel both ways, zoom, rotations, bounded bitmap cache; list grows {small} -> {large}; no Tk errors',flush=True)
