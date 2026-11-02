import tempfile,time,tkinter as tk,shutil,ctypes as C
from pathlib import Path
from tkinter import ttk
from openpyxl import load_workbook
import studio
from workspace_preview import SAMPLES

def pump(root,condition=lambda:False,timeout=.15):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  root.update();time.sleep(.01)
  if condition():return
with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
 project=studio.PROJECTS/'Тест';(project/'Документы').mkdir(parents=True);(project/'project.json').write_text('{}');file=project/'Документы/Реестр.xlsx';shutil.copy2(SAMPLES.parent/'Реестр.xlsx',file)
 source=load_workbook(file);expected=source.active['B12'].value;source.close()
 root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:(errors.append(str(e[1])),__import__('traceback').print_exception(*e));app.ensure_project_passports=lambda p:None;app.ask_save=lambda title,callback:callback('save');app.enter(project)
 pump(root,lambda:app.current in app.latest,100);s=app.current;assert s in app.latest,errors
 # Issue four operations without waiting for any PDF or manually moving selection.
 initial=app.revisions[s]
 for delete in (True,True,False,False):app.queue_register_operation(s,delete)
 pump(root,lambda:not getattr(s,'row_operation_busy',False) and not s.row_operations and app.saved_rev.get(s)==app.revisions[s],120)
 assert app.revisions[s]==initial+4 and app.saved_rev.get(s)==app.revisions[s],(app.revisions[s],app.saved_rev.get(s),errors)
 assert not s.row_operation_busy and not s.row_operations
 w=load_workbook(file,data_only=True);ws=w.active
 assert ws['B10'].value is None and ws['B11'].value is None and ws['B12'].value==expected
 assert [ws[f'A{r}'].value for r in (10,11,12)]==[1,2,3]
 assert ws['A36'].value==1,ws['A36'].value
 w.close();print('PASS queued first-row delete/delete/insert/insert, shifted content, first ordinal and next section restart, latest revision saved',flush=True)
 # Header minimize is panel-local for all four panels, including PDF.
 model=dict(app.models[s])
 for n in (0,1,2,3):
  host=app.holders[n];bar=next(c for c in host.winfo_children() if getattr(c,'panel_header',False));minimize=next(c for c in bar.winfo_children() if isinstance(c,ttk.Button) and c.cget('text')=='—');minimize.invoke();pump(root)
  assert root.state()!='iconic' and n in app.collapsed
  restore=next(c for c in host.winfo_children() if isinstance(c,ttk.Button) and c.winfo_manager()=='pack');assert restore.cget('text').startswith('Вернуть');restore.invoke();pump(root)
  assert n not in app.collapsed and app.models[s]==model
 # Floating panel minimizes alone and native title bar retains only close.
 app.detach(0);pump(root);floating=app.windows[0];app.collapse_panel(0);pump(root);assert floating.state()=='withdrawn' and root.state()!='iconic';app.restore_panel(0);pump(root);assert floating.state()=='normal'
 u=C.windll.user32;u.GetParent.argtypes=[C.c_void_p];u.GetParent.restype=C.c_void_p;u.GetWindowLongPtrW.argtypes=[C.c_void_p,C.c_int];u.GetWindowLongPtrW.restype=C.c_ssize_t
 style=u.GetWindowLongPtrW(u.GetParent(floating.winfo_id()),-16);assert not style & (0x10000|0x20000) and style & 0x80000
 app.dock(0);pump(root);assert str(app.split.cget('sashrelief'))=='flat' and int(app.split.cget('proxyborderwidth'))==0
 assert not errors,errors
 print('PASS all docked/floating panels minimize locally and restore, models preserved, close-only caption, flat separator',flush=True)
 app.close();pump(root,timeout=10)
