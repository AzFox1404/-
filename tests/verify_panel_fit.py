import tempfile,time,tkinter as tk
from pathlib import Path
from tkinter import ttk
import studio
from workspace_preview import SAMPLES

def pump(root,condition=lambda:False,timeout=.5):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  root.update();time.sleep(.02)
  if condition():return
with tempfile.TemporaryDirectory() as td:
 studio.STORE=Path(td)/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]));app.ensure_project_passports=lambda p:None
 app.import_item('file',next(SAMPLES.rglob('АОСР*.xlsx')));pump(root,lambda:hasattr(app,'latest') and app.current in app.latest,60)
 assert app.current in app.latest,errors
 def check(host,body):
  for row in host.winfo_children():
   if row is body:continue
   for w in row.winfo_children():
    if w.winfo_manager()=='pack':assert w.winfo_x()>=0 and w.winfo_x()+w.winfo_width()<=row.winfo_width(),(str(w),row.winfo_width(),w.winfo_x(),w.winfo_width())
 for n in (0,1,2,3):check(app.holders[n],app.body.get(n))
 left=app.holders[0].master
 before=int(app.split.panecget(left,'minsize'))
 app.split.sash_place(0,600,0);pump(root);app.enforce_panel_sizes();pump(root)
 assert int(app.split.panecget(left,'minsize'))==before
 app.split.sash_place(0,before,0);pump(root);check(app.holders[0],app.body[0])
 assert app.holders[0].winfo_width()<=before+10,(before,app.holders[0].winfo_width())
 app.detach(0);pump(root);win=app.windows[0];win.geometry('190x400');pump(root);app.enforce_panel_sizes();pump(root);check(win,app.body[0])
 returns=[w for row in win.winfo_children() for w in row.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')=='Вернуть'];assert returns and returns[0].cget('width')==0
 app.dock(0);pump(root);app.toggle_fullscreen();pump(root)
 btn=next(c for row in app.holders[0].winfo_children() for c in row.winfo_children() if getattr(c,'has_hint',False));btn.event_generate('<Enter>');pump(root,timeout=.6)
 tip=btn.hint_state['window'];assert tip and tip.winfo_viewable() and tip.attributes('-topmost')
 assert not root.attributes('-topmost')
 app.toggle_fullscreen();pump(root)
 assert not errors,errors
 app.close();pump(root,timeout=12)
 print('PASS initial toolbar bounds, detached minimum and full Return label, fullscreen hints above app without making app topmost',flush=True)
