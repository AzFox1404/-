from pathlib import Path
import tempfile,queue,subprocess
from openpyxl import Workbook
import manual_fields
from workspace_preview import Session
with tempfile.TemporaryDirectory() as td:
 p=Path(td);manual_fields.FILE=p/'rules.json';manual_fields.FILE.write_text('{"_names":{"ID_User_test":"Моё поле"}}','utf-8');book=Workbook();book.active['B2']='Исходное значение';book.active['C3']='=1+2';f=p/'custom.xlsx';book.save(f)
 r=subprocess.run(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(__import__('app_paths').APP_DIR/'BindExcel.ps1'),'-Source',str(f),'-Cell','B2','-Field','ID_User_test'],capture_output=True,timeout=50);assert r.returncode==0,r.stderr
 s=Session(f,queue.Queue(),prepared=True)
 try:
  while True:
   _,k,v=s.events.get(timeout=60)
   if k=='error':raise AssertionError(v)
   if k=='fields':assert v['ID_User_test']=='Исходное значение' and s.labels['ID_User_test']=='Моё поле'
   if k=='pdf':break
 finally:s.tasks.put(None);s.thread.join(15)
 print('PASS Excel explicit named binding, friendly label and Office preview',flush=True)
