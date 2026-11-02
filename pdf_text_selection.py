"""Mouse text selection shared by both PDF canvases (native text and OCR scans)."""
import hashlib
import json
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import tkinter as tk
import pypdfium2 as pdfium

OCR_LOCK=threading.Lock()


class PDFTextSelection:
    def __init__(self,canvas,app):
        self.canvas=canvas;self.app=app;self.pages={};self.source=None
        self.anchor=None;self.end=None;self.text='';self.generation=0
        self.results=queue.Queue();self.pending=set();self.timer=None
        self.message=tk.StringVar(master=canvas,value='Выделите текст мышью · Ctrl+C — копировать')
        canvas.configure(cursor='xterm')
        for event,fn in [('<Button-1>',self.begin),('<B1-Motion>',self.drag),('<ButtonRelease-1>',self.release),
                         ('<Double-Button-1>',self.word),('<Button-3>',self.menu),('<<Copy>>',self.copy),
                         ('<KeyPress>',self.key),('<Escape>',self.clear)]:
            canvas.bind(event,fn,add='+')
        canvas.bind('<Destroy>',self.destroy,add='+')

    def destroy(self,event):
        if event.widget is self.canvas:
            self.generation+=1
            if self.timer is not None:self.canvas.after_cancel(self.timer);self.timer=None

    def reset(self,source):
        self.generation+=1;self.source=source;self.pages={};self.pending=set();self.clear()

    def clear(self,event=None):
        self.anchor=None;self.end=None;self.forced_range=None;self.text='';self.canvas.delete('pdf-selection')
        self.message.set('Выделите текст мышью · Ctrl+C — копировать')
        return 'break'

    def register(self,n,page,bitmap,x,y,rotation=0):
        # Store device-normalized boxes so the same layer works at any scale.
        w,h=bitmap.width,bitmap.height;chars=[];tp=page.get_textpage()
        try:
            converter=bitmap.get_posconv(page)
            for i in range(tp.count_chars()):
                ch=tp.get_text_range(i,1)
                if not ch:continue
                l,b,r,t=tp.get_charbox(i)
                points=[converter.to_bitmap(a,c) for a,c in ((l,b),(l,t),(r,b),(r,t))]
                xs,ys=zip(*points)
                chars.append((ch,(min(xs)/w,min(ys)/h,max(xs)/w,max(ys)/h)))
        finally:tp.close()
        if not any(c.strip() for c,_ in chars):chars=[]
        previous=self.pages.get(n)
        # Preserve OCR already completed while lazy bitmaps leave/re-enter view.
        if not any(c.strip() for c,_ in chars) and previous:chars=previous['chars']
        self.pages[n]=dict(x=x,y=y,w=w,h=h,chars=chars,rotation=rotation)
        self.highlight()

    def page_at(self,x,y):
        for n,p in self.pages.items():
            if p['x']<=x<=p['x']+p['w'] and p['y']<=y<=p['y']+p['h']:return n
        return None

    def point(self,event):
        return (self.canvas.canvasx(event.x),self.canvas.canvasy(event.y))

    def begin(self,event):
        self.canvas.focus_set();self.clear();self.word_selected=False
        self.anchor=self.end=self.point(event)
        n=self.page_at(*self.anchor)
        if n is not None and not self.pages[n]['chars']:self.request_ocr(n)
        return 'break'

    def drag(self,event):
        if self.anchor is None:return 'break'
        self.forced_range=None
        if event.y<0:self.canvas.yview_scroll(-20 if int(self.canvas.cget('yscrollincrement'))==1 else -1,'units')
        elif event.y>self.canvas.winfo_height():self.canvas.yview_scroll(20 if int(self.canvas.cget('yscrollincrement'))==1 else 1,'units')
        self.end=self.point(event)
        n=self.page_at(*self.end)
        if n is not None and not self.pages[n]['chars']:self.request_ocr(n)
        self.highlight();return 'break'

    def release(self,event):
        if getattr(self,'word_selected',False):
            self.word_selected=False;return 'break'
        if self.anchor is not None:self.end=self.point(event);self.highlight()
        return 'break'

    def nearest(self,point):
        x,y=point;n=self.page_at(x,y)
        if n is None:
            if not self.pages:return None
            n=min(self.pages,key=lambda n:abs(self.pages[n]['y']-y))
        p=self.pages[n];x=(x-p['x'])/p['w'];y=(y-p['y'])/p['h']
        candidates=[(i,b) for i,(c,b) in enumerate(p['chars']) if c.strip() and b[3]>b[1]]
        if not candidates:return None
        i,_=min(candidates,key=lambda v:(max(v[1][0]-x,0,x-v[1][2])**2+max(v[1][1]-y,0,y-v[1][3])**2))
        return n,i

    def highlight(self):
        self.canvas.delete('pdf-selection');self.text=''
        if self.anchor is None or self.end is None:return
        forced=getattr(self,'forced_range',None)
        if not forced and abs(self.anchor[0]-self.end[0])+abs(self.anchor[1]-self.end[1])<3:return
        a,b=forced if forced else (self.nearest(self.anchor),self.nearest(self.end))
        if a is None or b is None:return
        a,b=sorted((a,b));parts=[]
        for n in sorted(self.pages):
            if not a[0]<=n<=b[0]:continue
            p=self.pages[n];lo=a[1] if n==a[0] else 0;hi=b[1]+1 if n==b[0] else len(p['chars'])
            chosen=p['chars'][lo:hi];parts.append(''.join(c for c,_ in chosen))
            for c,(l,t,r,bottom) in chosen:
                if not c.strip() or r<=l or bottom<=t:continue
                self.canvas.create_rectangle(p['x']+l*p['w'],p['y']+t*p['h'],p['x']+r*p['w'],p['y']+bottom*p['h'],
                                             fill='#79acf3',stipple='gray50',outline='',tags='pdf-selection')
        self.text='\n'.join(parts).replace('\r\n','\n').replace('\r','\n').strip()
        if self.text:self.message.set('Текст выделен · Ctrl+C — копировать')

    def word(self,event):
        pos=self.nearest(self.point(event))
        if pos is None:return 'break'
        n,i=pos;p=self.pages[n];chars=p['chars'];a=b=i
        while a>0 and not chars[a-1][0].isspace():a-=1
        while b+1<len(chars) and not chars[b+1][0].isspace():b+=1
        l,t,_,bottom=chars[a][1];_,_,r,_=chars[b][1]
        self.anchor=(p['x']+l*p['w'],p['y']+(t+bottom)/2*p['h'])
        self.end=(p['x']+r*p['w'],self.anchor[1]);self.forced_range=((n,a),(n,b));self.word_selected=True;self.highlight();return 'break'

    def copy(self,event=None):
        if self.text:
            self.canvas.clipboard_clear();self.canvas.clipboard_append(self.text)
            self.message.set('Скопировано · Ctrl+V — вставить в поле')
        return 'break'

    def key(self,event):
        from clipboard_keys import operation
        if operation(event)=='copy':return self.copy()
        return None

    def menu(self,event):
        self.canvas.focus_set()
        menu=tk.Menu(self.canvas,tearoff=False)
        menu.add_command(label='Копировать',command=self.copy,state='normal' if self.text else 'disabled')
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:menu.grab_release()
        return 'break'

    def request_ocr(self,n):
        if n in self.pending:return
        self.pending.add(n);generation=self.generation;p=self.pages[n]
        self.message.set('Распознавание текста страницы…')
        try:
            if isinstance(self.source,(str,Path)):
                path=Path(self.source);identity=f'{path.resolve()}:{path.stat().st_mtime_ns}:{path.stat().st_size}'
            else:identity=hashlib.sha256(self.source).hexdigest()
            digest=hashlib.sha256(f'{identity}:{n}:{p["rotation"]}:selection-v1'.encode()).hexdigest()
            cache=Path(self.app.catalog_dir)/'Кэш выделения текста'/(digest+'.json')
            if cache.exists():
                self.apply_ocr(n,json.loads(cache.read_text('utf-8')));return
            doc=pdfium.PdfDocument(self.source)
            try:
                page=doc[n]
                try:
                    bmp=page.render(scale=min(2.6,2400/max(page.get_size())),rotation=p['rotation'])
                    try:image=bmp.to_pil().copy()
                    finally:bmp.close()
                finally:page.close()
            finally:doc.close()
        except Exception:
            self.pending.discard(n);self.message.set('Не удалось подготовить страницу для распознавания.');return
        def work():
            try:
                with OCR_LOCK, tempfile.TemporaryDirectory() as tmp:
                    file=Path(tmp)/'page.png';image.save(file);image.close()
                    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(Path(__file__).with_name('PassportOCR.ps1'))],
                                          input=str(file.resolve())+'\n',capture_output=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
                    data=json.loads(result.stdout.lstrip('\ufeff'))
                    if 'error' in data:raise ValueError(data['error'])
                    try:
                        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_text(json.dumps(data,ensure_ascii=False),'utf-8')
                    except OSError:pass
                    self.results.put((generation,n,data,None))
            except Exception as exc:self.results.put((generation,n,None,str(exc)))
        threading.Thread(target=work,daemon=True).start()
        if self.timer is None:self.timer=self.canvas.after(100,self.poll)

    def apply_ocr(self,n,data):
        p=self.pages[n];chars=[];previous=None
        for word in data.get('words',[]):
            value=word['text'];line=word['line']
            if previous is not None:chars.append((' ' if line==previous else '\n',(0,0,0,0)))
            for i,c in enumerate(value):
                l=(word['x']+word['w']*i/max(1,len(value)))/data['width']
                r=(word['x']+word['w']*(i+1)/max(1,len(value)))/data['width']
                chars.append((c,(l,word['y']/data['height'],r,(word['y']+word['h'])/data['height'])))
            previous=line
        p['chars']=chars;self.pending.discard(n)
        self.message.set('Текст скана распознан · выделите нужные символы мышью' if chars else 'На странице не удалось распознать текст.')
        self.highlight()

    def poll(self):
        self.timer=None
        while not self.results.empty():
            generation,n,data,error=self.results.get()
            if generation!=self.generation or n not in self.pages:continue
            if error:self.pending.discard(n);self.message.set('Не удалось распознать текст страницы. Попробуйте ещё раз.')
            else:self.apply_ocr(n,data)
        if self.pending:self.timer=self.canvas.after(100,self.poll)
