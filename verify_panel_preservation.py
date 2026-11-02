from pathlib import Path
import tempfile,shutil,time,tkinter as tk
from tkinter import ttk
import studio
from workspace_preview import SAMPLES,DATES

def pump(root,condition=lambda:False,seconds=.15):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  root.update();time.sleep(.01)
  if condition():return
with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p;studio.PROJECTS=p/'Проекты';studio.LIB=p/'Библиотека/Шаблоны';project=studio.PROJECTS/'Тест';(project/'Документы').mkdir(parents=True);(project/'project.json').write_text('{}')
 source=next(SAMPLES.rglob('АОСР*.xlsx'));shutil.copy2(source,project/'Документы'/source.name)
 root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:(errors.append(str(e[1])),__import__('traceback').print_exception(*e));app.ensure_project_passports=lambda p:None;app.ask_save=lambda t,cb:cb('save');app.enter(project)
 pump(root,lambda:app.current in app.latest,60);assert app.current in app.latest,errors
 key=next(k for k in app.views if k in DATES);app.views[key].set('01.');old_views=app.views;old_pdf=app.pdf_viewer;model=dict(app.models[app.current])
 for n in (0,1,2,3):
  host=app.holders[n];packed=list(host.pack_slaves());app.collapse_panel(n);pump(root)
  assert root.state()!='iconic' and len(host.pack_slaves())==1
  restore=host.pack_slaves()[0];assert restore.cget('text').startswith('Вернуть');restore.invoke();pump(root)
  assert list(host.pack_slaves())==packed
 assert app.views is old_views and app.views[key].get()=='01.' and app.pdf_viewer is old_pdf
 assert app.models[app.current]==model and not errors,errors
 # A preview refresh after a source change must wait for async page metadata.
 app.draw();pump(root)
 app.close();pump(root,seconds=8)
 print('PASS local panel collapse preserves widget order, partial date text, models and the live PDF renderer; no callback errors',flush=True)
