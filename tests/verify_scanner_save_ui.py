"""Search visibility, owner-centred confirmation and responsive 40-document save."""
import tempfile,time,threading,tkinter as tk
from tkinter import ttk
from pathlib import Path
from pypdf import PdfWriter,PdfReader
import studio,scanner_ui
from app_dialogs import messagebox

def children(w):
 for c in w.winfo_children():yield c;yield from children(c)
def pump(root,until,timeout=15):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  root.update();time.sleep(.005)
  if until():return
 raise AssertionError('UI timeout')

with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны';studio.SAMPLES=p/'absent/sample'
 project=studio.PROJECTS/'Test';base=project/'Документы';base.mkdir(parents=True);(project/'project.json').write_text('{}')
 (base/'Needle.docx').write_bytes(b'fixture')
 root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:(errors.append(str(e[1])),__import__('traceback').print_exception(*e),root.after_idle(root.destroy));root.update()
 entry=app.targets[3];entry.insert(0,'Needle');root.update()
 tree=next(w for w in children(app.landing) if isinstance(w,ttk.Treeview))
 leaf=next(n for n in tree.get_children(str(base.resolve())) if 'Needle' in tree.item(n,'text'))
 assert tree.bbox(leaf),'matching file hidden by collapsed ancestors'
 entry.delete(0,'end');root.update()
 pdf=p/'source.pdf';writer=PdfWriter()
 for _ in range(40):writer.add_blank_page(200,300)
 with pdf.open('wb') as out:writer.write(out)
 scanner_ui.inspect=lambda *a:[dict(path=str(pdf),source=pdf.name,start=i,end=i,type='Паспорт качества',number='',date='',material='',pages=['']*40) for i in range(1,41)]
 scanner_ui.scanner(app,files=[pdf],destination=p/'out')
 pump(root,lambda:any(getattr(w,'hint_message','')=='Сохранить отмеченные документы отдельными PDF' for w in children(app.active_scan)))
 win=app.active_scan;win.geometry('1000x650+650+280');root.update();time.sleep(.1);root.update()
 original=scanner_ui.save_records;main=threading.get_ident();started=[]
 def save(records,output):
  assert threading.get_ident()!=main
  started.append(time.monotonic());time.sleep(.4)
  return original(records,output)
 scanner_ui.save_records=save
 checked=[];pulses=[]
 def beat():pulses.append(time.monotonic());root.after(20,beat)
 beat()
 def answer():
  dialogs=[w for w in win.winfo_children() if isinstance(w,tk.Toplevel) and w.winfo_viewable() and not w.overrideredirect()]
  if not dialogs:root.after(20,answer);return
  d=dialogs[0]
  if not getattr(d,'test_settled',False):d.test_settled=True;root.after(120,answer);return
  assert abs((d.winfo_rootx()+d.winfo_width()/2)-(win.winfo_rootx()+win.winfo_width()/2))<25
  assert abs((d.winfo_rooty()+d.winfo_height()/2)-(win.winfo_rooty()+win.winfo_height()/2))<25,(d.geometry(),win.geometry(),str(d.master))
  checked.append(d.title())
  label='Да' if d.title()=='Неполные реквизиты' else 'Понятно'
  next(w for w in children(d) if isinstance(w,ttk.Button) and w.cget('text')==label).invoke()
  if label=='Да':root.after(30,answer)
 root.after(50,answer)
 button=next(w for w in children(win) if getattr(w,'hint_message','')=='Сохранить отмеченные документы отдельными PDF')
 button.event_generate('<ButtonPress-1>',x=10,y=10);button.event_generate('<ButtonRelease-1>',x=10,y=10)
 pump(root,lambda:not win.winfo_exists())
 assert checked==['Неполные реквизиты','Готово'],checked
 assert len(app.quality_records())==40 and len(list((p/'out').rglob('*.pdf')))==40
 assert sum(t>=started[0] and t<started[0]+.4 for t in pulses)>=8,'Tk frozen while saving'
 assert all(len(PdfReader(f).pages)==1 for f in (p/'out').rglob('*.pdf'))
 root.destroy();assert not errors,errors
print('PASS visible search result, centred scanner confirmations, Yes -> 40 PDFs, library and responsive UI')
