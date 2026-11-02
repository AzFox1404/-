from pathlib import Path
import tkinter as tk,tempfile,shutil,json
from tkinter import ttk,messagebox
import studio
from workspace_preview import SAMPLES
def all_widgets(w):
 for c in w.winfo_children():yield c;yield from all_widgets(c)
with tempfile.TemporaryDirectory() as td:
 studio.STORE=Path(td)/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
 root=tk.Tk();a=studio.Studio(root);errors=[]
 root.report_callback_exception=lambda *e:(errors.append(e[1]),__import__('traceback').print_exception(*e))
 messagebox.showinfo=lambda *args,**kwargs:None
 messagebox.askyesno=lambda *args,**kwargs:True
 folder=Path(td)/'Исходники';folder.mkdir()
 shutil.copy2(next((SAMPLES.parent/'Шаблоны').glob('*АОСР*')),folder/'Акт.xlsx')
 shutil.copy2(next(SAMPLES.rglob('АКП Г-Э*.pdf')),folder/'Паспорт грунт-эмаль.pdf')
 a.import_item('folder',folder)
 def check():
  win=getattr(a,'active_scan',None)
  save=next((w for w in all_widgets(win) if isinstance(w,ttk.Button) and w.cget('text')=='Подтвердить и сохранить'),None) if win and win.winfo_exists() else None
  if not save:root.after(150,check);return
  try:
   save.invoke();root.update()
   records=a.quality_records()
   assert len(records)==1 and records[0]['number']=='495',records
   assert a.quality_choices('materials')==a.quality_choices('attachments')
   assert 'Паспорт качества №495 от 25.09.2024' in a.quality_choices('materials')
   assert list((a.project/'Документы').glob('*. Паспорта'))
   print('PASS automatic source scan, split folder, catalogue, both field choices',flush=True)
   # Only the exception icon is permanent; row icons appear only in registry forms.
   canvases=[w for w in all_widgets(a.holders[1]) if isinstance(w,tk.Canvas) and hasattr(w,'redraw_theme')]
   assert len(canvases)==6,len(canvases)
   a.close()
   for w in list(all_widgets(a.decision)):
    if isinstance(w,ttk.Button) and w.cget('text')=='Не сохранять':w.invoke();break
  except Exception:
   import traceback;traceback.print_exc();root.destroy();raise
 root.after(150,check);root.after(90000,root.destroy);root.mainloop()
 assert not errors,errors

