from test_pdf_wait import wait_pdf
import tempfile,time,tkinter as tk
from tkinter import ttk
from pathlib import Path
from types import SimpleNamespace
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image,ImageDraw,ImageFont,ImageGrab
import studio
from pdf_page_preview import PagePreview
from workspace_preview import Workspace

def pump(root,seconds=.2):
 end=time.monotonic()+seconds
 while time.monotonic()<end:root.update();time.sleep(.015)
def choose(viewer,needle):
 wait_pdf(root,viewer if hasattr(viewer,'selection') else viewer.pdf_viewer)
 sel=viewer.selection if hasattr(viewer,'selection') else viewer.preview_selection
 n=next(n for n,p in sel.pages.items() if needle in ''.join(c for c,b in p['chars']))
 p=sel.pages[n];text=''.join(c for c,b in p['chars']);start=text.index(needle);end=start+len(needle)-1
 a=p['chars'][start][1];b=p['chars'][end][1]
 def point(box):return (round(p['x']+(box[0]+box[2])/2*p['w']-sel.canvas.canvasx(0)),round(p['y']+(box[1]+box[3])/2*p['h']-sel.canvas.canvasy(0)))
 x,y=point(a);xx,yy=point(b)
 sel.canvas.event_generate('<Button-1>',x=x,y=y)
 sel.canvas.event_generate('<B1-Motion>',x=xx,y=yy)
 sel.canvas.event_generate('<ButtonRelease-1>',x=xx,y=yy)
 sel.canvas.event_generate('<<Copy>>');pump(root)
 assert sel.canvas.clipboard_get()==needle,(needle,sel.text)
 assert sel.canvas.find_withtag('pdf-selection')
 return sel
with tempfile.TemporaryDirectory() as td:
 folder=Path(td);native=folder/'native.pdf';scan=folder/'scan.pdf'
 pdfmetrics.registerFont(TTFont('TestArial','C:/Windows/Fonts/arial.ttf'))
 c=canvas.Canvas(str(native),pagesize=(600,600));c.setFont('TestArial',20)
 c.drawString(45,530,'Сертификат качества № 869');c.drawString(45,490,'Дата 14.01.2024');c.save()
 im=Image.new('RGB',(1800,1800),'white');d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',70)
 d.text((120,180),'Сертификат качества № 869',font=font,fill='black');d.text((120,300),'Дата выдачи 14.01.2024',font=font,fill='black');im.save(folder/'scan.png')
 c=canvas.Canvas(str(scan),pagesize=(600,600));c.drawImage(str(folder/'scan.png'),0,0,600,600);c.save()
 studio.STORE=folder/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека'/'Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[]
 root.report_callback_exception=lambda *e:(errors.append(str(e[1])),__import__('traceback').print_exception(*e))
 top=tk.Toplevel(root);top.geometry('1000x800');v=PagePreview(top,app);v.pack(fill='both',expand=True);v.show(native,0);pump(root)
 choose(v,'869');choose(v,'14.01.2024');choose(v,'Сертификат')
 # A single character can be selected by dragging within its glyph box.
 sel=v.selection;p=sel.pages[0];chars=p['chars'];i=''.join(c for c,b in chars).index('№');box=chars[i][1]
 x=round(p['x']+box[0]*p['w']+1);xx=round(p['x']+box[2]*p['w']-1);y=round(p['y']+(box[1]+box[3])/2*p['h'])
 sel.canvas.event_generate('<Button-1>',x=x,y=y);sel.canvas.event_generate('<B1-Motion>',x=xx,y=y);sel.canvas.event_generate('<ButtonRelease-1>',x=xx,y=y)
 sel.copy();assert root.clipboard_get()=='№',sel.text
 choose(v,'Сертификат')
 entry=ttk.Entry(top);entry.pack();entry.focus_set();entry.event_generate('<<Paste>>');pump(root);assert entry.get()=='Сертификат'
 # Character boxes follow actual page rotation, not an unrotated text overlay.
 for angle in (90,90,90,90):
  v.rotate(angle);pump(root);choose(v,'869')
 v.show(scan,0);wait_pdf(root,v);pump(root)
 v.canvas.event_generate('<Button-1>',x=100,y=80);pump(root)
 until=time.monotonic()+45
 while v.selection.pending and time.monotonic()<until:pump(root,.1)
 assert v.selection.pages[0]['chars'],v.selection.message.get()
 choose(v,'869');choose(v,'14.01.2024')
 assert list((app.catalog_dir/'Кэш выделения текста').glob('*.json'))
 # Actual working-environment PDF preview methods with a generated PDF, no Office dependency.
 other=tk.Toplevel(root);other.geometry('1000x800');host=tk.Frame(other);host.pack(fill='both',expand=True)
 worker=SimpleNamespace(body={2:host},zoom=70,latest={'act':native.read_bytes()},current='act',models={},catalog_dir=app.catalog_dir,icon_button=app.icon_button)
 worker.draw=lambda:Workspace.draw(worker);worker.rescale=lambda z:Workspace.rescale(worker,z)
 Workspace.preview(worker);pump(root);choose(worker,'14.01.2024')
 choose(worker,'869');studio.Studio.command(worker,2,'copy');assert root.clipboard_get()=='869'
 # Ctrl+C routing, including Windows keycode used by Russian keyboard layout.
 worker.preview_selection.key(SimpleNamespace(keycode=67,keysym='c',state=4));assert root.clipboard_get()=='869'
 Path('review').mkdir(exist_ok=True);other.lift();pump(root)
 x,y=other.winfo_rootx(),other.winfo_rooty();ImageGrab.grab((x,y,x+other.winfo_width(),y+other.winfo_height())).save('review/pdf-text-selection.png')
 assert not errors,errors
 top.destroy();other.destroy();app.close()
 print('PASS native Cyrillic/symbol/date selection, four rotations, real Windows OCR scan, cache, both PDF viewers, clipboard and field paste',flush=True)
