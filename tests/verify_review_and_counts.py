from pathlib import Path
from workspace_preview import SAMPLES,Session
from office_forms import extra_fields
from openpyxl import load_workbook
import tempfile,shutil,queue,pymupdf as fitz

def receive(s,kind):
 while True:
  _,k,v=s.events.get(timeout=120)
  if k=='error':raise AssertionError(v)
  if k==kind:return v

def evidence(pdf,token):
 d=fitz.open(stream=pdf,filetype='pdf');colours=[];yellow=[]
 for page in d:
  for block in page.get_text('dict')['blocks']:
   for line in block.get('lines',[]):
    for span in line['spans']:
     if token in span['text']:colours.append(span['color'])
  yellow += [x['rect'] for x in page.get_drawings() if x.get('fill') and x['fill'][0]>.95 and x['fill'][1]>.95 and x['fill'][2]<.1]
 d.close();return colours,yellow
with tempfile.TemporaryDirectory() as td:
 source=next(SAMPLES.rglob('Реестр документов качества к АОСР №КМ-1.xlsx'))
 word=next((SAMPLES.parent/'ИД Великоросс').rglob('Приложение №1 к АОСР*.docx'))
 for i,source in enumerate((source,word)):
  p=Path(td)/source.name;shutil.copy2(source,p);s=Session(p,queue.Queue(),prepared=True)
  try:
   values=receive(s,'fields');receive(s,'pdf')
   key=next(k for k in values if k.startswith('row') and k.endswith('_2'));row=int(key.split('_')[0][3:]);token='REVIEWTEST'
   values[key]=token;s.preview_context=dict(activeRow=row,activeKey=key)
   if i==0:values[f'row{row}_6']='5'
   s.tasks.put((values,1));rev,clean=receive(s,'pdf');assert rev==1 and s.review_pdf
   colours,yellow=evidence(s.review_pdf[1],token);assert 0xff0000 in colours and yellow,(colours,yellow)
   colours,clean_yellow=evidence(clean,token);assert colours and 0xff0000 not in colours and not clean_yellow,(colours,clean_yellow)
   before=yellow;s.preview_context=dict(activeRow=row+1,activeKey='');s.tasks.put((values,1));receive(s,'pdf')
   colours,yellow=evidence(s.review_pdf[1],token);assert 0xff0000 in colours and yellow!=before
  finally:s.tasks.put(None);s.thread.join(30)
  if i==0:
   w=load_workbook(p,data_only=True);ws=w.active;assert ws['B9'].font.color is None or ws['B9'].font.color.type!='rgb' or ws['B9'].font.color.rgb[-6:]!='FF0000';assert ws['B9'].fill.fgColor.rgb not in ('00FFFF00','FFFFFF00');total=next(r[0].row for r in ws.iter_rows() if any(c.value=='Всего страниц:' for c in r));assert ws[f'F{total}'].value==38;w.close()
  print('PASS red edited text + yellow active row; row switch; clean saved file and clean PDF:',source.suffix,flush=True)
 # Every page entry is derived, including formerly literal/manual values.
 p=Path(td)/'main.xlsx';shutil.copy2(SAMPLES.parent/'Реестр.xlsx',p)
 assert not any(v['label']=='Страницы' for v in extra_fields(p).values())
 s=Session(p,queue.Queue(),prepared=True)
 try:
  vals=receive(s,'fields');receive(s,'pdf');vals['row11_5']='5';s.tasks.put((vals,1));receive(s,'pdf')
 finally:s.tasks.put(None);s.thread.join(30)
 w=load_workbook(p,data_only=True);ws=w.active;assert ws['F11'].value==6 and ws['F12'].value==7,(ws['F11'].value,ws['F12'].value);w.close()
 print('PASS pages are hidden and recalculate from sheet count across subsequent rows')
