from app_paths import EXAMPLES_ROOT
import tempfile,tkinter as tk,shutil,json,hashlib,time
from pathlib import Path
import studio
from tkinter import ttk
root_source=EXAMPLES_ROOT
with tempfile.TemporaryDirectory() as td:
 folder=Path(td);source=folder/'Проект';source.mkdir();originals={}
 for name in ('ИД Великоросс','КНС'):
  for file in (root_source/name).rglob('*'):
   if file.suffix not in ('.doc','.docx'):continue
   originals[file]=hashlib.sha256(file.read_bytes()).hexdigest();target=source/name/file.relative_to(root_source/name);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
 studio.STORE=folder/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[];app.ensure_project_passports=lambda p:None
 root.report_callback_exception=lambda *e:(errors.append(str(e[1])),__import__('traceback').print_exception(*e))
 app.import_item('folder',source)
 end=time.monotonic()+100
 while time.monotonic()<end:
  root.update();time.sleep(.04)
  if hasattr(app,'latest') and app.current in app.latest:break
 assert hasattr(app,'latest') and app.current in app.latest,errors
 data=json.loads((app.project/'document-analysis.json').read_text('utf-8'))
 assert data['complete'] and len(data['documents'])==5
 assert all(item['plan']['fields'] for item in data['documents'].values()),data
 assert all(item['plan']['kind']!='unknown' for item in data['documents'].values())
 assert any(item['plan']['warnings'] for item in data['documents'].values())
 assert app.views and any('Представитель' in v for v in app.current.labels.values())
 assert hasattr(app.current,'analysis')
 # Open a quality register and verify that only one editable position is presented.
 path=next(app.project.rglob('Приложение №1 к АОСР*.docx'));app.open(path)
 end=time.monotonic()+50
 while time.monotonic()<end:
  root.update();time.sleep(.04)
  if app.current.source==path and app.current in app.latest:break
 assert any(k.startswith('row2_') for k in app.views)
 assert not any(k.startswith('row3_') for k in app.views)
 assert len(__import__('docx').Document(path).tables[0].columns)==5
 for file,sha in originals.items():assert hashlib.sha256(file.read_bytes()).hexdigest()==sha
 assert not errors,errors
 # Close only the isolated project/window created by this test.
 app.close()
 end=time.monotonic()+12
 while time.monotonic()<end:
  try:root.update();time.sleep(.03)
  except tk.TclError:break
 print('PASS import all five samples, cached maps, warnings without correction, form fields, quality row selector, five columns, original hashes unchanged',flush=True)
