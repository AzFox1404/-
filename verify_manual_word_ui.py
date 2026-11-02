import tempfile,time,tkinter as tk
from tkinter import ttk,messagebox
from pathlib import Path
from docx import Document
import studio,manual_fields

def widgets(w):
 for c in w.winfo_children():yield c;yield from widgets(c)
def pump(root,condition,timeout=60):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  root.update();time.sleep(.04)
  if condition():return
 raise AssertionError('Timeout')
with tempfile.TemporaryDirectory() as td:
 p=Path(td);manual_fields.FILE=p/'rules.json';f=p/'unknown.docx';d=Document();d.add_paragraph('Пример неизвестной формы');d.add_paragraph('Значение');d.add_paragraph('Подпись ответственного лица');d.save(f)
 studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
 root=tk.Tk();app=studio.Studio(root);app.ensure_project_passports=lambda p:None;errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]))
 app.import_item('file',f);pump(root,lambda:hasattr(app,'latest') and app.current in app.latest)
 assert not app.models[app.current]
 manual_fields.dialog(app)
 pump(root,lambda:any(isinstance(w,tk.Toplevel) and w.title()=='Дополнительное поле Word' for w in root.winfo_children()))
 win=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and w.title()=='Дополнительное поле Word');lb=next(w for w in widgets(win) if isinstance(w,tk.Listbox));values=lb.get(0,'end');assert not any('Подпись ответственного лица' in v for v in values)
 i=values.index('Значение');lb.selection_set(i);lb.event_generate('<<ListboxSelect>>');root.update()
 text=next(w for w in widgets(win) if isinstance(w,tk.Text));text.tag_add('sel','1.0','1.8')
 entry=next(w for w in widgets(win) if isinstance(w,ttk.Entry));entry.insert(0,'Моё поле');messagebox.askyesno=lambda *a,**kw:True
 next(w for w in widgets(win) if isinstance(w,ttk.Button) and w.cget('text')=='Проверить и сохранить привязку').invoke()
 pump(root,lambda:app.current in app.latest and bool(app.models[app.current]))
 assert 'Значение' in app.models[app.current].values();assert 'Моё поле' in app.current.labels.values();assert not errors,errors
 app.close()
 end=time.monotonic()+15
 while time.monotonic()<end:
  try:root.update();time.sleep(.04)
  except tk.TclError:break
  if not app.sessions:break
 print('PASS manual Word wizard, static signature excluded, explicit mapping, restart worker and editable field',flush=True)
