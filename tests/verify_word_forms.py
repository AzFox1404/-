from app_paths import EXAMPLES_ROOT
from pathlib import Path
import tempfile,shutil,queue,time,json
from workspace_preview import Session
from pypdf import PdfReader
root=EXAMPLES_ROOT
results=[]
for folder in (('КНС',) if '--kns' in __import__('sys').argv else ('ИД Великоросс','КНС')):
 for p in (root/folder).rglob('*'):
  if p.suffix not in ('.doc','.docx'):continue
  with tempfile.TemporaryDirectory() as td:
   target=Path(td)/p.name;shutil.copy2(p,target);events=queue.Queue();s=Session(target,events,prepared=True)
   def receive(kind,timeout=80):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
     other,k,payload=events.get(timeout=max(1,until-time.monotonic()))
     if k=='error':raise AssertionError(payload)
     if k==kind:return payload
    raise AssertionError('timeout '+kind)
   try:
    fields=receive('fields');rev,data=receive('pdf');print('OPEN',p.name,len(fields),len(PdfReader(__import__('io').BytesIO(data)).pages),flush=True)
    assert fields
    vals=dict(fields)
    if s.analysis['kind']=='act':
     assert 'actDate' in vals and 'workStart' in vals and 'workEnd' in vals,vals.keys()
     vals['actDate']='06.12.2027';vals['workStart']='01.11.2027';vals['workEnd']='06.12.2027'
     vals['address']='Проверочный объект, Санкт-Петербург';vals['notes']='Проверка изменения поля'
    else:vals['row2_2']='Проверочный материал';vals['row2_5']='06.12.2027'
    s.tasks.put((vals,1));rev,data=receive('pdf');assert rev==1
    text='\n'.join(page.extract_text() for page in PdfReader(__import__('io').BytesIO(data)).pages)
    assert ('Проверочный объект' if s.analysis['kind']=='act' else 'Проверочный материал') in text,text[:500]
    assert '2027' in text
    if s.analysis['kind']=='act':assert 'Проверка изменения поля' in text
    if s.analysis['kind']=='quality':
     s.tasks.put(dict(row=2,revision=2));mapped,row=receive('rows');assert row==3
     assert mapped['row3_2']=='' and mapped['row4_2']==fields['row3_2'],{k:v for k,v in mapped.items() if k.startswith(('row2_','row3_','row4_'))}
     receive('pdf')
    results.append(dict(name=p.name,kind=s.analysis['kind'],fields=len(fields),pages=len(PdfReader(__import__('io').BytesIO(data)).pages)))
   finally:s.tasks.put(None);s.thread.join(20)
   assert not s.thread.is_alive()
   check=Session(target,queue.Queue(),prepared=True)
   try:
    while True:
     _,k,payload=check.events.get(timeout=80)
     if k=='error':raise AssertionError(payload)
     if k=='fields':
      assert (payload.get('address')=='Проверочный объект, Санкт-Петербург' if s.analysis['kind']=='act' else payload.get('row2_2')=='Проверочный материал'),payload
      if s.analysis['kind']=='act':assert payload['actDate']=='06.12.2027' and payload['workStart']=='01.11.2027' and payload['notes']=='Проверка изменения поля',payload
     if k=='pdf':break
   finally:check.tasks.put(None);check.thread.join(20)
Path('review/word-worker-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),'utf-8')
print('PASS all five Word samples open, update, render, date format; quality row insertion',flush=True)
