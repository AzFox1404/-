import tkinter as tk,tempfile,subprocess,sys,ctypes as C
from pathlib import Path
from tkinter import ttk
import studio
from workspace_preview import SAMPLES
with tempfile.TemporaryDirectory() as td:
 studio.STORE=Path(td)/'s';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
 root=tk.Tk();app=studio.Studio(root)
 app.import_item('file',next((SAMPLES.parent/'Шаблоны').glob('*АОСР*')))
 helper=[None];errors=[]
 root.report_callback_exception=lambda *e:(errors.append(e[1]),print(repr(e[1]),flush=True))
 def fgpid():
  u=C.windll.user32;u.GetForegroundWindow.restype=C.c_void_p
  pid=C.c_uint();u.GetWindowThreadProcessId(C.c_void_p(u.GetForegroundWindow()),C.byref(pid));return pid.value
 def ready():
  if app.current not in app.latest:root.after(120,ready);return
  helper[0]=subprocess.Popen([sys.executable,'-c',"import tkinter as t;r=t.Tk();r.title('Проверка другого приложения');r.geometry('400x200+30+30');r.mainloop()"],creationflags=subprocess.CREATE_NO_WINDOW)
  root.after(1000,start)
 def start():
  assert fgpid()==helper[0].pid,(fgpid(),helper[0].pid)
  app.views['materials'].set('Тест обновления '+('слово '*60))
  root.after(900,check)
 def check():
  if app.saved_rev.get(app.current,-1)!=app.revisions[app.current]:root.after(150,check);return
  assert fgpid()==helper[0].pid,(fgpid(),helper[0].pid)
  print('PASS: another application stays foreground throughout Office export and PDF update',flush=True)
  helper[0].terminate();helper[0].wait();app.close()
  def children(w):
   for c in w.winfo_children():yield c;yield from children(c)
  next(b for b in children(app.decision) if isinstance(b,ttk.Button) and b.cget('text')=='Не сохранять').invoke()
 root.after(150,ready);root.after(60000,root.destroy)
 try:root.mainloop()
 finally:
  if helper[0] and helper[0].poll() is None:helper[0].terminate();helper[0].wait()
 assert not errors,errors
