from pathlib import Path
import tempfile,tkinter as tk
from tkinter import ttk
import studio
from workspace_preview import SAMPLES
from openpyxl import load_workbook
def widgets(w):
 for child in w.winfo_children():yield child;yield from widgets(child)
with tempfile.TemporaryDirectory() as td:
 studio.STORE=Path(td)/'s';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[]
 root.report_callback_exception=lambda *e:(errors.append(e[1]),__import__('traceback').print_exception(*e))
 app.import_item('file',next((SAMPLES.parent/'Шаблоны').glob('*АОСР*')))
 def ready():
  if app.current not in app.latest:root.after(120,ready);return
  app.views['materials'].set('Документ №1')
  field=next(w for w in widgets(app.body[1]) if isinstance(w,ttk.Combobox) and str(w.cget('textvariable'))==str(app.views['materials']))
  field.tk.call(field.cget('postcommand'));field.set('Паспорт №2 от 01.02.2026');field.event_generate('<<ComboboxSelected>>')
  assert field.get()=='Документ №1, Паспорт №2 от 01.02.2026 г.'
  assert field.index('insert')==field.index('end')
  assert field.index('sel.first')==len('Документ №1, ')
  assert field.index('sel.last')==len(field.get())
  root.geometry('300x200');root.update()
  assert root.winfo_width()>=root.minsize()[0]
  for n in (0,1,2):
   bar=app.holders[n].winfo_children()[0]
   assert bar.winfo_width()>=bar.winfo_reqwidth(),(n,bar.winfo_width(),bar.winfo_reqwidth())
  root.after(800,finish)
 def finish():
  if app.saved_rev.get(app.current,-1)!=app.revisions[app.current]:root.after(120,finish);return
  s=load_workbook(app.current.copy).active;assert '01.02.2026 г.' in s['F52'].value
  print('PASS year suffix in Excel; caret and inserted segment; minimum panel/window widths',flush=True)
  app.close()
  next(w for w in widgets(app.decision) if isinstance(w,ttk.Button) and w.cget('text')=='Не сохранять').invoke()
 root.after(120,ready);root.after(60000,root.destroy);root.mainloop();assert not errors,errors
