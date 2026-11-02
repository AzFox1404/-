import tempfile,tkinter as tk,threading,json,shutil
from pathlib import Path
from tkinter import ttk
import studio
from workspace_preview import SAMPLES
from package_build import PackageDialog
from pdf_page_preview import PagePreview
from passports import save_records
from pypdf import PdfReader
from office_forms import extra_fields
with tempfile.TemporaryDirectory() as td:
 studio.STORE=Path(td)/'s';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
 root=tk.Tk();a=studio.Studio(root);errors=[]
 root.report_callback_exception=lambda *e:(errors.append(e[1]),__import__('traceback').print_exception(*e))
 pdf=next(SAMPLES.rglob('АКП Г-Э*.pdf'));top=tk.Toplevel(root);viewer=PagePreview(top,a);viewer.pack(fill='both',expand=True)
 rotations={};viewer.show(pdf,0,rotations);original=(viewer.image.width(),viewer.image.height())
 viewer.rotate(90);assert (viewer.image.height(),viewer.image.width())==original
 folder,records=save_records([dict(path=str(pdf),source=pdf.name,start=1,end=1,type='Паспорт качества',number='495',date='25.09.2024',material='Грунт-эмаль',rotations=rotations)],td)
 assert PdfReader(folder/records[0]['file']).pages[0].rotation==90;top.destroy()
 # This real register contains sections at 8/34/90. Only the preceding one is visible.
 register=SAMPLES.parent/'Реестр.xlsx'
 a.import_item('file',register)
 def ready():
  if a.current not in a.latest:root.after(120,ready);return
  try:
   a.row_choice[a.current]=116;a.build(1)
   assert [k for k in a.views if k.startswith('part')]==['part90'],a.views.keys()
   dlg=PackageDialog(a)
   # Only the common register in this test. Count regenerates the selected empty inventory.
   def finished():
    text=dlg.totals_text.get()
    if 'Документов:' not in text:
     if 'Не удалось' in text:raise AssertionError(text)
     root.after(150,finished);return
    print(text,flush=True)
    dlg.close_dialog();a.close()
   root.after(150,finished)
  except Exception:
   root.destroy();raise
 root.after(120,ready);root.after(90000,root.destroy);root.mainloop();assert not errors,errors
 print('PASS rotated preview/output; nearest section; exact package statistics',flush=True)
