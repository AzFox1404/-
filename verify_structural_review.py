from pathlib import Path
import tempfile,shutil,queue
import pymupdf as fitz
from workspace_preview import Session,SAMPLES

def get(s,kind):
 while True:
  _,k,v=s.events.get(timeout=120)
  if k=='error':raise AssertionError(v)
  if k==kind:return v

def red_text(pdf):
 doc=fitz.open(stream=pdf,filetype='pdf');spans=[]
 for p in doc:
  for block in p.get_text('dict')['blocks']:
   for line in block.get('lines',[]):
    spans += [s['text'] for s in line['spans'] if s['color']==0xff0000]
 doc.close();return spans
with tempfile.TemporaryDirectory() as td:
 sources=[next(SAMPLES.rglob('Реестр документов качества к АОСР №КМ-1.xlsx')),next((SAMPLES.parent/'ИД Великоросс').rglob('Приложение №1 к АОСР*.docx'))]
 for source in sources:
  path=Path(td)/source.name;shutil.copy2(source,path);s=Session(path,queue.Queue(),prepared=True)
  try:
   values=get(s,'fields');get(s,'pdf');rows=sorted({int(k.split('_')[0][3:]) for k in values if k.startswith('row')})
   for number,delete in enumerate((True,False),1):
    s.tasks.put(dict(row=rows[4],delete=delete,revision=number));fields,selected=get(s,'rows');get(s,'pdf')
    assert s.structural_review and s.preview_context['activeRow']==selected
    red=red_text(s.review_pdf[1]);assert all(all(c.isdigit() or c.isspace() or c in '.,' for c in text) for text in red),red
    if source.suffix=='.xlsx':assert red,red
    print('PASS',source.suffix,'delete' if delete else 'insert','red only at totals:',red,flush=True)
  finally:s.tasks.put(None);s.thread.join(30)
