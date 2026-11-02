from pathlib import Path
import tempfile,shutil,queue
from workspace_preview import SAMPLES,Session
from openpyxl import load_workbook
with tempfile.TemporaryDirectory() as td:
 for source in (SAMPLES.parent/'Реестр.xlsx',next(SAMPLES.rglob('Реестр документов качества к АОСР №КМ-1.xlsx'))):
  p=Path(td)/source.name;shutil.copy2(source,p);w=load_workbook(p);ws=w.active;ws['A16']='=#REF!+1';ws['A16'].number_format='dd.mm.yyyy'
  general=source.name=='Реестр.xlsx'
  if general:ws['F16']='=#REF!+E16'
  w.save(p);w.close();s=Session(p,queue.Queue(),prepared=True)
  try:
   while True:
    _,kind,data=s.events.get(timeout=100)
    if kind=='error':raise AssertionError(data)
    if kind=='fields':assert s.register_repaired and 'row16_2' in data
    if kind=='pdf':break
  finally:s.tasks.put(None);s.thread.join(30)
  w=load_workbook(p,data_only=True);assert isinstance(w.active['A16'].value,(int,float))
  if general:assert isinstance(w.active['F16'].value,(int,float))
  w.close();print('PASS automatic repair on opening, fields reloaded and PDF exported:',source.name,flush=True)
