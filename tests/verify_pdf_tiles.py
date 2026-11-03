import tempfile,time,tkinter as tk
from pathlib import Path
import pymupdf as fitz
import studio
from pdf_page_preview import PagePreview

def wait(root,fn,seconds=15):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  root.update();time.sleep(.005)
  if fn():return
 raise AssertionError('Timed out')

with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
 f=p/'A0.pdf';doc=fitz.open();page=doc.new_page(width=2384,height=3370)
 for y in range(10,3300,30):page.draw_line((10,y),(2300,y));page.insert_text((30,y+15),'SCHEME 0123456789',fontsize=10)
 doc.save(f);doc.close();before=f.read_bytes()
 root=tk.Tk();app=studio.Studio(root);top=tk.Toplevel(root);top.geometry('850x650');v=PagePreview(top,app);v.pack(fill='both',expand=True);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]))
 started=time.monotonic();v.show(f,0);wait(root,lambda:bool(v.tiles.visible) and bool(v.tiles.overviews))
 print('METRIC generated A0 first visible ms:',round((time.monotonic()-started)*1000),flush=True)
 assert not v.images and v.tiles.bytes<48*1024*1024
 for photo in v.tiles.cache.values():assert photo.width()<=513 and photo.height()<=513
 pid=v.renderer.process.pid
 for rotation in (0,90,180,270):
  v.rotations['0']=rotation;v.set_zoom(120);wait(root,lambda:bool(v.tiles.visible) and not v.tiles.pending)
  assert v.selection.pages[0]['w']==v.pages[0][1]
  from PIL import Image
  key=next(iter(v.tiles.visible));photo=v.tiles.visible[key][1]
  shot=p/'tile.png';v.canvas.tk.call(str(photo),'write',str(shot),'-format','png')
  reference=fitz.open(f);rp=reference[0];rp.set_rotation(rotation)
  expected=rp.get_pixmap(matrix=fitz.Matrix(120/75,120/75),clip=fitz.Rect(key[3:])/(120/75),alpha=False)
  with Image.open(shot) as actual:assert actual.convert('RGB').tobytes()==expected.samples,'tile differs from canonical render'
  reference.close()
  v.canvas.yview_moveto(.6);v.render_visible();wait(root,lambda:bool(v.tiles.visible) and not v.tiles.pending)
  assert v.tiles.bytes<=48*1024*1024
 assert v.renderer.process.pid==pid and f.read_bytes()==before
 old=dict(v.tiles.visible);v.canvas.yview_scroll(1,'units');v.render_visible()
 shared=set(old)&set(v.tiles.visible)
 assert shared and all(old[k][1] is v.tiles.visible[k][1] for k in shared),'pan must preserve exact bitmap objects'
 wait(root,lambda:not v.tiles.pending)
 v.set_zoom(135)
 assert v.canvas.find_withtag('pdf-transition'),'zoom must retain a visible previous frame'
 wait(root,lambda:bool(v.tiles.visible) and not v.tiles.pending)
 top.destroy();root.update();assert not errors,errors
 app.close();print('PASS A0 visible-only tiles, bounded bitmap memory, cached overview, canonical text geometry, four rotations, scroll and cleanup; same worker and unchanged PDF')
