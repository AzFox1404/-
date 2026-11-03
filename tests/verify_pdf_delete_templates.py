"""Generated PDF deletion/rollback and lossless template migration."""
import tempfile,time,tkinter as tk
from pathlib import Path
import pymupdf as fitz
import studio
from template_library import organize

with tempfile.TemporaryDirectory() as td:
 p=Path(td);library=p/'templates';old=library/'Old project';old.mkdir(parents=True)
 for name in ['Титул.docx','АОСР.xlsx','АООК.xlsx','Приложение.docx','Реестр.xlsx','Приказ.docx']:(old/name).write_bytes(name.encode())
 organize(library);organize(library)
 assert not old.exists()
 assert {f.parent.name for f in library.rglob('*') if f.is_file()}=={'Титулы','АОСР','АООК','Приложения','Реестры','Приказы'}
 studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
 project=p/'project';base=project/'Документы';base.mkdir(parents=True);(project/'project.json').write_text('{}')
 path=base/'Scheme.pdf';d=fitz.open();page=d.new_page();page.insert_text((50,50),'SCHEME');d.save(path);d.close();original=path.read_bytes()
 root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]));app.enter(project);app.open(path)
 end=time.monotonic()+20
 while time.monotonic()<end:
  root.update();time.sleep(.01)
  view=getattr(app,'reference_view',None)
  if view and view.pages:break
 assert view.pages,errors
 app.perform_file_operation(path,'delete');root.update()
 assert not path.exists() and not app.reference_path,errors
 app.journal().restore();assert path.read_bytes()==original
 app.journal().temp.cleanup();app.project=None;root.destroy()
 assert not errors,errors
 print('PASS categorized/idempotent templates; delete displayed PDF without lock; exact project rollback')
