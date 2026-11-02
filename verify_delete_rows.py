from pathlib import Path
import tempfile,shutil,queue
from workspace_preview import Session,SAMPLES
from openpyxl import load_workbook
from docx import Document
sources=[SAMPLES.parent/'1. КМ'/'1. Монтаж колонн'/'Реестр документов №1 к АОСР №КМ-1.xlsx',next((SAMPLES.parent/'ИД Великоросс').rglob('Приложение №1 к АОСР*.docx'))]
# Locate the quality register independent of the sample subfolder name.
if not sources[0].exists():sources[0]=next(SAMPLES.rglob('Реестр документов качества к АОСР №КМ-1.xlsx'))
with tempfile.TemporaryDirectory() as td:
 for index,source in enumerate(sources):
  f=Path(td)/source.name;shutil.copy2(source,f);s=Session(f,queue.Queue(),prepared=True)
  def receive(kind):
   while True:
    _,k,v=s.events.get(timeout=70)
    if k=='error':raise AssertionError(v)
    if k==kind:return v
  try:
   vals=receive('fields');receive('pdf');rows=sorted({int(k.split('_')[0][3:]) for k in vals if k.startswith('row')});first=rows[0];second=rows[1];expected=vals[f'row{second}_2']
   s.tasks.put(dict(row=first,delete=True,revision=1));fields,selected=receive('rows');receive('pdf')
   assert fields[f'row{first}_2'].strip()==expected.strip(),(index,fields.get(f'row{first}_2'),expected)
   assert len({k.split('_')[0] for k in fields if k.startswith('row')})==len(rows)-1
  finally:s.tasks.put(None);s.thread.join(20)
  if index==0:
   w=load_workbook(f,data_only=False);sheet=w.active
   nums=[c[0].value for c in sheet.iter_rows(min_row=9,max_col=1) if c[0].value is not None];assert nums[0]=='=1';w.close()
  else:assert len(Document(f).tables[0].columns)==5
  print('PASS delete, shift, ordinal rebuild and original columns:',source.suffix,flush=True)
