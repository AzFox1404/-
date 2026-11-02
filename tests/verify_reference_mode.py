from pathlib import Path
import tempfile,time,tkinter as tk
from pypdf import PdfWriter
import studio
from workspace_preview import SAMPLES
with tempfile.TemporaryDirectory() as td:
 studio.STORE=Path(td)/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]));app.ensure_project_passports=lambda p:None
 app.import_item('file',next(SAMPLES.rglob('АОСР*.xlsx')))
 end=time.monotonic()+65
 while time.monotonic()<end:
  root.update();time.sleep(.04)
  if hasattr(app,'latest') and app.current in app.latest:break
 assert hasattr(app,'latest') and app.current in app.latest,errors
 old=app.current;values=dict(app.models[old]);file=app.project/'Документы/ИС.pdf';w=PdfWriter();w.add_blank_page(500,700);w.add_blank_page(500,700)
 with file.open('wb') as out:w.write(out)
 app.show_reference(file);root.update();assert app.current is old and old.thread.is_alive();assert app.models[old]==values
 app.open(old.source);root.update();assert not app.reference_path and app.views and app.models[old]==values
 assert not errors,errors
 app.close()
 if getattr(app,'decision',None):
  def choose(w):
   from tkinter import ttk
   if isinstance(w,ttk.Button) and w.cget('text')=='Сохранить':w.invoke();return True
   return any(choose(c) for c in w.winfo_children())
  choose(app.decision)
 end=time.monotonic()+20
 while time.monotonic()<end:
  try:root.update();time.sleep(.04)
  except tk.TclError:break
  if not old.thread.is_alive():break
 print('PASS drawing preview preserves live act session, fields and return; no Tk callbacks failed',flush=True)
