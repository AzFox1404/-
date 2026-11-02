import tempfile,tkinter as tk
from pathlib import Path
from tkinter import ttk,messagebox
import studio
from workspace_preview import SAMPLES
from openpyxl import load_workbook

def widgets(w):
 for child in w.winfo_children():yield child;yield from widgets(child)
with tempfile.TemporaryDirectory() as td:
 studio.STORE=Path(td)/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
 r=tk.Tk();a=studio.Studio(r);errors=[]
 r.report_callback_exception=lambda *e:(errors.append(e[1]),__import__('traceback').print_exception(*e))
 a.import_item('file',next((SAMPLES.parent/'Шаблоны').glob('*АОСР*')))
 project=a.project;original=a.current.source;original_bytes=a.journal().copies[original.relative_to(project/'Документы')].read_bytes()
 messagebox.askyesno=lambda *x,**kw:True
 def wait(fn):
  if a.current and a.current in a.latest and a.saved_rev.get(a.current,-1)==a.revisions[a.current] and not a.stopping:fn()
  else:r.after(120,lambda:wait(fn))
 def begin():
  a.views['materials'].set('Паспорт №1')
  box=next(w for w in widgets(a.body[1]) if isinstance(w,ttk.Combobox) and str(w.cget('textvariable'))==str(a.views['materials']))
  box.tk.call(box.cget('postcommand'));box.set('Сертификат №2');box.event_generate('<<ComboboxSelected>>')
  assert a.views['materials'].get()=='Паспорт №1, Сертификат №2',a.views['materials'].get()
  a.folder_name=lambda *x:'Новая';a.new_folder()
  folder=project/'Документы'/'Новая';assert folder.is_dir()
  a.perform_file_operation(original,'move',folder/original.name)
  r.after(150,lambda:wait(moved))
 def moved():
  folder=project/'Документы'/'Новая'
  assert (folder/original.name).exists() and not original.exists()
  a.selected[0]=str(project/'Документы');a.path_clipboard=(folder,False);a.paste_document()
  r.after(150,lambda:wait(copied))
 def copied():
  copied_dir=project/'Документы'/'Новая (2)'
  assert copied_dir.is_dir()
  a.selected[0]=str(copied_dir);a.delete_document()
  assert not copied_dir.exists()
  a.close()
  next(w for w in widgets(a.decision) if isinstance(w,ttk.Button) and w.cget('text')=='Не сохранять').invoke()
  r.after(200,check_restore)
 def check_restore():
  if a.stopping:r.after(100,check_restore);return
 r.after(150,lambda:wait(begin));r.after(90000,r.destroy);r.mainloop()
 assert original.read_bytes()==original_bytes
 assert not (project/'Документы'/'Новая').exists()
 assert not errors,errors
 print('PASS append choices, folder create/move/copy/delete, full project discard',flush=True)
