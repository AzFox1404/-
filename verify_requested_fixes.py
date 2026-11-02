from workspace_preview import *
from tempfile import TemporaryDirectory
from openpyxl import load_workbook
from pypdf import PdfReader
from io import BytesIO
with TemporaryDirectory() as td:
 for typ in ('act','reg'):
  source=next((SAMPLES.parent/'Шаблоны').glob('*АОСР*')) if typ=='act' else next(SAMPLES.rglob('Реестр документов качества к АОСР №КМ-1.xlsx'))
  file=Path(td)/(typ+'.xlsx');shutil.copy2(source,file);q=queue.Queue();s=Session(file,q,True)
  def get():
   _,k,v=q.get(timeout=90);assert k!='error',v;return k,v
  try:
   _,vals=get();get()
   if typ=='act':
    for rev,text in enumerate(['Сертификат испытания '+('р'*310),'Короткий текст','Повторное заполнение '+('слово '*150)],1):
     vals['materials']=text;vals['address']=text
     s.tasks.put((vals,rev));_,data=get()
     assert ('р'*30 in ''.join(p.extract_text() or '' for p in PdfReader(BytesIO(data[1])).pages)) if rev==1 else True
     wb=load_workbook(file);sh=wb.active
     names=[n for n in wb.defined_names if n.startswith('BID_more_materials')]
     if rev==2:assert not names
     else:assert names
     for n in names:
      ref=list(wb.defined_names[n].destinations)[0][1].replace('$','').split(':')[0]
      assert sh[ref].font.u is None
    print('PASS material overflow and long-short-long without glyph underline',flush=True)
   else:
    for rev,row in [(1,10),(3,12)]:
     s.tasks.put(dict(row=row,revision=rev));_,(vals,_)=get();get()
     vals[f'row{row+1}_6']='3'
     s.tasks.put((vals,rev+1));get()
    sh=load_workbook(file,data_only=True).active
    total=next(c.row for row in sh for c in row if c.value=='Всего страниц:')
    assert [sh.cell(r,1).value for r in range(9,total)]==list(range(1,total-8))
    assert sh.cell(total,6).value==41
    print('PASS inserted ordinals sequential; SUM=41',flush=True)
  finally:s.tasks.put(None);s.thread.join(30)
