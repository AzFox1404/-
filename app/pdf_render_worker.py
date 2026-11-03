"""Isolated PDF renderer. Binary pipe; no Tk, Office or shared native PDF state."""
import pickle,sys
from collections import OrderedDict
import pymupdf as fitz

def run():
 doc=None;lists=OrderedDict();texts={}
 while True:
  try:req=pickle.load(sys.stdin.buffer)
  except EOFError:break
  try:
   if req['op']=='open':
    if doc:doc.close()
    lists.clear();texts.clear()
    source=req['source']
    if not isinstance(source,bytes):
     from pathlib import Path
     source=Path(source).read_bytes()
    doc=fitz.open(stream=source,filetype='pdf')
    result=dict(op='open',generation=req['generation'],sizes=[tuple(doc[n].rect)[2:] for n in range(len(doc))])
   elif req['op']=='locate':
    from fast_preview import locate
    result=dict(op='locate',generation=req['generation'],anchors=locate(doc,req['values']))
   else:
    page=doc[req['page']];page.set_rotation((page.rotation+req['rotation'])%360)
    try:
     key=(req['page'],req['rotation'])
     if key not in lists:lists[key]=page.get_displaylist()
     lists.move_to_end(key)
     while len(lists)>4:
      old,_=lists.popitem(last=False);texts.pop(old,None)
     scale=req['zoom']/75
     tile=req.get('tile');clip=fitz.Rect(tile)/scale if tile else None
     detail=.25 if req.get('overview') and tile else 1
     pix=lists[key].get_pixmap(matrix=fitz.Matrix(scale*detail,scale*detail),clip=clip,alpha=False)
     if req.get('text',True) and key not in texts:
      chars=[];matrix=page.rotation_matrix;w,h=page.rect.width,page.rect.height
      raw=page.get_text('rawdict',flags=fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES)
      for block in raw['blocks']:
       for line in block.get('lines',[]):
        for span in line['spans']:
         for char in span['chars']:
          r=fitz.Rect(char['bbox'])*matrix;chars.append((char['c'],(r.x0/w,r.y0/h,r.x1/w,r.y1/h)))
        chars.append(('\n',(0,0,0,0)))
      texts[key]=chars if any(c.strip() for c,b in chars) else []
     result=dict(op='tile' if tile else 'overview' if req.get('overview') else 'page',generation=req['generation'],epoch=req['epoch'],page=req['page'],zoom=req['zoom'],rotation=req['rotation'],size=(pix.width,pix.height),rgb=pix.samples,chars=texts.get(key,[]) if req.get('text',True) else [],tile=tile,overview=req.get('overview',False),viewport=req.get('viewport',0))
    finally:page.set_rotation((page.rotation-req['rotation'])%360)
   pickle.dump(result,sys.stdout.buffer,protocol=5);sys.stdout.buffer.flush()
  except Exception as exc:
   pickle.dump(dict(op='error',generation=req.get('generation'),epoch=req.get('epoch'),error=str(exc)),sys.stdout.buffer,protocol=5);sys.stdout.buffer.flush()
 if doc:doc.close()
if __name__=='__main__':run()

