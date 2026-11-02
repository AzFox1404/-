import tempfile,tkinter as tk,time
from pathlib import Path
from tkinter import ttk
import studio
from workspace_preview import SAMPLES
from package_build import PackageDialog
from app_dialogs import ask_text
def descendants(w):
 for c in w.winfo_children():yield c;yield from descendants(c)
with tempfile.TemporaryDirectory() as td:
 studio.STORE=Path(td)/'s';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[]
 root.report_callback_exception=lambda *e:(errors.append(e[1]),__import__('traceback').print_exception(*e))
 app.import_item('file',SAMPLES.parent/'1. КЖ'/'Реестр.xlsx')
 def ready():
  if app.current not in app.latest:root.after(120,ready);return
  try:
   app.row_choice[app.current]=25;app.build(1)
   assert app.views['group24'].get().startswith('Паспорта') and 'group8' not in app.views
   dlg=PackageDialog(app)
   root.after(800,lambda:initial(dlg))
  except Exception:root.destroy();raise
 def initial(dlg):
  assert not dlg.stats_running and 'нажмите' in dlg.totals_text.get().lower()
  checks=[w for w in descendants(dlg.window) if isinstance(w,ttk.Checkbutton)]
  assert checks and all(not getattr(w,'has_hint',False) for w in checks)
  dlg.start_stats();assert dlg.stats_running
  assert 'примерно' in dlg.totals_text.get().lower()
  def done():
   if dlg.stats_running:root.after(150,done);return
   assert not getattr(dlg,'stats_error',''),dlg.totals_text.get()
   assert 'Страниц' in dlg.totals_text.get();dlg.close_dialog()
   def fill():
    top=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
    entry=next(w for w in descendants(top) if isinstance(w,ttk.Entry))
    entry.delete(0,'end');entry.insert(0,'Проверка')
    next(w for w in descendants(top) if isinstance(w,ttk.Button) and w.cget('text')=='Применить').invoke()
   root.after(100,fill)
   assert ask_text(app,'Название','Введите название','')=='Проверка'
   print('PASS nearest group; no automatic count; explicit count + ETA; no static hints; Russian dialog',flush=True)
   app.close()
  root.after(150,done)
 root.after(120,ready);root.after(60000,root.destroy);root.mainloop();assert not errors,errors

