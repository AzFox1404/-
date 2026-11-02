import tempfile,shutil,queue
from pathlib import Path
from workspace_preview import SAMPLES,Session
from docx import Document
source=next((SAMPLES.parent/'ИД Великоросс').rglob('Приложение №1 к АОСР*.docx'))
def get(s,kind):
 while True:
  _,k,v=s.events.get(timeout=120)
  if k=='error':raise AssertionError(v)
  if k==kind:return v
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/source.name;shutil.copy2(source,p);s=Session(p,queue.Queue(),prepared=True)
 try:
  fields=get(s,'fields');get(s,'pdf');rows=sorted({int(k.split('_')[0][3:]) for k in fields if k.startswith('row')});first=rows[0];expected=fields[f'row{rows[2]}_2']
  for rev,delete in enumerate((True,True,False,False),1):
   s.tasks.put(dict(row=first,delete=delete,revision=rev));fields,selected=get(s,'rows');get(s,'pdf');assert selected==first
  assert fields[f'row{first}_2']=='' and fields[f'row{first+1}_2']=='' and fields[f'row{first+2}_2']==expected
 finally:s.tasks.put(None);s.thread.join(30)
 d=Document(p);assert [r.cells[0].text for r in d.tables[0].rows[first-1:first+2]]==['1','2','3'];assert len(d.tables[0].columns)==5
 print('PASS Word first-row delete/delete/insert/insert: data shifted, selected row correct, ordinals 1/2/3 and columns preserved',flush=True)
