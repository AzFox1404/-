"""Isolated PDF renderer. Binary pipe; no Tk, Office or shared native PDF state."""
import pickle,sys
import pymupdf as fitz

def run():
 doc=None
 while True:
  try:req=pickle.load(sys.stdin.buffer)
  except EOFError:break
  try:
   if req['op']=='open':
    if doc:doc.close()
    source=req['source'];doc=fitz.open(stream=source,filetype='pdf') if isinstance(source,bytes) else fitz.open(source)
    result=dict(op='open',generation=req['generation'],sizes=[tuple(doc[n].rect)[2:] for n in range(len(doc))])
   else:
    page=doc[req['page']];page.set_rotation((page.rotation+req['rotation'])%360)
    try:
     pix=page.get_pixmap(matrix=fitz.Matrix(req['zoom']/75,req['zoom']/75),alpha=False)
     chars=[];matrix=page.rotation_matrix;w,h=page.rect.width,page.rect.height
     raw=page.get_text('rawdict',flags=fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES)
     for block in raw['blocks']:
      for line in block.get('lines',[]):
       for span in line['spans']:
        for char in span['chars']:
         r=fitz.Rect(char['bbox'])*matrix;chars.append((char['c'],(r.x0/w,r.y0/h,r.x1/w,r.y1/h)))
       chars.append(('\n',(0,0,0,0)))
     if not any(c.strip() for c,b in chars):chars=[]
     result=dict(op='page',generation=req['generation'],epoch=req['epoch'],page=req['page'],zoom=req['zoom'],rotation=req['rotation'],size=(pix.width,pix.height),rgb=pix.samples,chars=chars)
    finally:page.set_rotation((page.rotation-req['rotation'])%360)
   pickle.dump(result,sys.stdout.buffer,protocol=5);sys.stdout.buffer.flush()
  except Exception as exc:
   pickle.dump(dict(op='error',generation=req.get('generation'),epoch=req.get('epoch'),error=str(exc)),sys.stdout.buffer,protocol=5);sys.stdout.buffer.flush()
 if doc:doc.close()
if __name__=='__main__':run()
