import tempfile,time,tkinter as tk
from pathlib import Path
import studio,scanner_ui
from pypdf import PdfWriter
from tkinter import ttk
with tempfile.TemporaryDirectory() as td:
 p=Path(td);file=p/'source.pdf';w=PdfWriter()
 for _ in range(4):w.add_blank_page(500,700)
 with file.open('wb') as f:w.write(f)
 records=[dict(path=str(file),source='Паспорт.pdf',start=a,end=b,type='Паспорт качества',number=str(i),date='01.01.2024',material='Материал',pages=['']*4) for i,(a,b) in enumerate(((1,2),(3,4)),1)]
 scanner_ui.inspect=lambda *a:records;scanner_ui.messagebox.showinfo=lambda *a,**kw:None
 studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
 root=tk.Tk();app=studio.Studio(root);scanner_ui.scanner(app,files=[file],destination=p/'output')
 def all(w):
  for c in w.winfo_children():yield c;yield from all(c)
 end=time.monotonic()+6
 while time.monotonic()<end:
  root.update();time.sleep(.03)
  lb=next((c for c in all(app.active_scan) if isinstance(c,tk.Listbox)),None)
  if lb:break
 assert lb is not None
 lb.focus_force();root.update();lb.event_generate('<Down>');root.update();assert lb.curselection()==(1,),lb.curselection()
 lb.event_generate('<space>');root.update();assert records[1]['enabled'] is False
 button=next(c for c in all(app.active_scan) if getattr(c,'hint_message','')=='Сохранить отмеченные документы отдельными PDF')
 button.event_generate('<ButtonPress-1>',x=10,y=10);button.event_generate('<ButtonRelease-1>',x=10,y=10);root.update()
 end=time.monotonic()+10
 while not app.quality_records() and time.monotonic()<end:root.update();time.sleep(.01)
 assert len(app.quality_records())==1 and len(list((p/'output').rglob('*.pdf')))==1
 app.close();print('PASS scanner keyboard navigation, checkboxes and only checked documents exported')
