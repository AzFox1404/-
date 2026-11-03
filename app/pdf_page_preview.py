"""Continuous PDF preview with visible-page rendering and per-page rotation."""
from bisect import bisect_right
from collections import OrderedDict
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import Image,ImageTk
import queue
from pdf_renderer import PDFRenderer


class PagePreview(ttk.Frame):
    def __init__(self,parent,app,wheel_zoom=False):
        super().__init__(parent)
        self.app=app;self.path=None;self.number=0;self.rotations={};self.zoom=70;self.image=None
        self.pages=[];self.images={};self._pending=None;self._sizes=None;self._zoom_job=None;self._wanted_zoom=None;self._text_cache={}
        self._bitmap_cache=OrderedDict();self._bitmap_bytes=0
        self.quick_values={};self.quick_anchors={};self.quick_changes={};self._quick_requested=False;self._quick_fonts={}
        self.renderer=PDFRenderer();self._generation=0;self._epoch=0;self._requested=set();self._render_poll=None
        from pdf_tiles import Tiles
        self.tiles=Tiles(self)
        tools=ttk.Frame(self);tools.pack(fill='x')
        for key,label,fn in [('rotateleft','Повернуть текущую страницу на 90° влево',lambda:self.rotate(-90)),
                             ('rotateright','Повернуть текущую страницу на 90° вправо',lambda:self.rotate(90))]:
            app.icon_button(tools,key,label,fn)
        self.page_text=tk.StringVar(value='');ttk.Label(tools,textvariable=self.page_text).pack(side='left',padx=5)
        self.scale=ttk.Combobox(tools,values=(35,50,70,85,100,125,150,200),state='readonly',width=5)
        self.scale.set(self.zoom);self.scale.pack(side='right');self.scale.bind('<<ComboboxSelected>>',lambda e:self.set_zoom(int(self.scale.get())))
        area=ttk.Frame(self);area.pack(fill='both',expand=True)
        self.quick_notice=ttk.Label(self,text='Предварительный вид · вёрстка уточняется',padding=(6,2));self.quick_area=area
        self.canvas=tk.Canvas(area,bg='#e6ded8',highlightthickness=0,yscrollincrement=1)
        x=ttk.Scrollbar(area,orient='horizontal',command=self.canvas.xview)
        y=ttk.Scrollbar(area,command=self.canvas.yview)
        def scrolled(first,last):
            y.set(first,last);self.schedule_visible()
        self.canvas.configure(xscrollcommand=x.set,yscrollcommand=scrolled)
        x.pack(side='bottom',fill='x');y.pack(side='right',fill='y');self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<MouseWheel>',self.wheel)
        self.canvas.bind('<Control-MouseWheel>',self.zoom_at)
        for key,dx,dy in [('Up',0,-60),('Down',0,60),('Left',-30,0),('Right',30,0)]:
            self.canvas.bind('<'+key+'>',lambda e,x=dx,y=dy:self.arrow_scroll(x,y))
        self.canvas.bind('<Configure>',lambda e:self.schedule_visible())
        self.canvas.bind('<Button-1>',self.select_page)
        self.bind('<Destroy>',self.cleanup,add='+')
        from pdf_text_selection import PDFTextSelection
        self.selection=PDFTextSelection(self.canvas,app)
        self.canvas.bind('<FocusIn>',lambda e:setattr(app,'active_panel',2),add='+')
        app.icon_button(tools,'copy','Копировать выделенный текст · Ctrl+C',self.selection.copy)
        info=ttk.Label(self,textvariable=self.selection.message,wraplength=260);info.pack(fill='x')
        self.canvas.bind('<Configure>',lambda e:info.configure(wraplength=max(120,e.width-8)),add='+')
        self._render_poll=self.after(16,self.poll_renderer)
        from auto_scroll import install
        install(self.canvas)

    def cleanup(self,event):
        if event.widget is self:
            self.renderer.close()
            if self._render_poll is not None:self.after_cancel(self._render_poll);self._render_poll=None
            # Release native Tk resources here, not later in a background GC
            # triggered while an Office worker parses the next document.
            self.images.clear();self._bitmap_cache.clear();self.image=None
            self.tiles.reset(True)
            self._quick_fonts.clear()
            self.page_text=None;self.selection.message=None
        if event.widget is self and self._zoom_job is not None:
            self.after_cancel(self._zoom_job);self._zoom_job=None
        if event.widget is self and self._pending is not None:
            self.after_cancel(self._pending);self._pending=None

    def wheel(self,event):
        self.canvas.yview_scroll(-max(1,abs(event.delta)//120)*60 if event.delta>0 else max(1,abs(event.delta)//120)*60,'units')
        self.schedule_visible()
        return 'break'

    def arrow_scroll(self,x,y):
        if y:self.canvas.yview_scroll(y,'units')
        if x:self.canvas.xview_scroll(x,'units')
        self.schedule_visible();return 'break'

    def select_page(self,event):
        if self.pages:
            self.number=self.page_at(self.canvas.canvasy(event.y));self.update_label()

    def page_at(self,y):
        return max(0,min(len(self.pages)-1,bisect_right(self.starts,y)-1))

    def update_label(self):
        self.page_text.set(f'{self.number+1} / {len(self.pages)}')
        self.image=self.images.get(self.number)

    def show(self,path,number,rotations=None):
        source=path if isinstance(path,bytes) else Path(path)
        same=source==self.path and (rotations or {})==self.rotations and bool(self.pages)
        if same:
            self.number=number;self.selection.clear();self.go_to(number);return
        changed=source!=self.path
        self.path=source;self.number=number;self.rotations=rotations if rotations is not None else {}
        if changed:
            self.tiles.reset(True)
            self.quick_anchors={};self.quick_changes={};self._quick_requested=False;self.quick_notice.pack_forget()
            self._restore_fraction=None
            self._sizes=None;self._text_cache.clear();self._bitmap_cache.clear();self._bitmap_bytes=0
            self._generation+=1;self.pages=[];self.images.clear();self.canvas.delete('all');self.selection.reset(source)
            self.page_text.set("Загрузка PDF…");self.renderer.open(source,self._generation)
        else:self.render()

    def zoom_at(self,event):
        level=self._wanted_zoom if self._wanted_zoom is not None else self.zoom
        self._wanted_zoom=max(25,min(200,level+(10 if event.delta>0 else -10)))
        self._zoom_anchor=(event.x,event.y)
        if self._zoom_job is not None:self.after_cancel(self._zoom_job)
        def apply():
            self._zoom_job=None;level=self._wanted_zoom;self._wanted_zoom=None;self.set_zoom(level,self._zoom_anchor)
        self._zoom_job=self.after(65,apply);return 'break'

    def set_zoom(self,value,anchor=None):
        point=None
        if anchor and self.pages:
            x,y=anchor;cx=self.canvas.canvasx(x);cy=self.canvas.canvasy(y);n=self.page_at(cy);top,w,h,_=self.pages[n]
            point=(n,(cx-8)/w,(cy-top)/h,x,y)
        self.zoom=max(25,min(200,value));self.scale.set(self.zoom)
        if hasattr(self,'on_zoom'):self.on_zoom(self.zoom)
        self.render(defer=bool(point))
        if point:
            n,fx,fy,x,y=point;top,w,h,_=self.pages[n]
            total=max(p[1] for p in self.pages)+16
            self.canvas.xview_moveto((8+fx*w-x)/total);self.canvas.yview_moveto((top+fy*h-y)/self.height)
            self.render_visible()

    def step(self,direction):
        if self.pages:self.go_to(self.number+direction)

    def go_to(self,number):
        if not self.pages:self.number=max(0,number);return
        self.number=max(0,min(len(self.pages)-1,number))
        self.canvas.yview_moveto((self.pages[self.number][0]-8)/self.height)
        self.render_visible()

    def rotate(self,degrees):
        key=str(self.number);self.rotations[key]=(self.rotations.get(key,0)+degrees)%360;self.render()

    def render(self,defer=False):
        if self.path is None:return
        if self._sizes is None:return
        self._epoch+=1;self.renderer.epoch=self._epoch;self._requested.clear()
        previous=[(k,photo) for k,(_,photo) in self.tiles.visible.items()]
        for n,photo in self.images.items():
            rotation=self.rotations.get(str(n),0)
            if self.selection.pages.get(n,{}).get('rotation')==rotation:
                original_width=self._sizes[n][1] if rotation%180 else self._sizes[n][0]
                previous.append(((n,photo.width()/original_width*75,rotation,0,0,photo.width(),photo.height()),photo))
        self.number=max(0,min(len(self._sizes)-1,self.number));self.pages=[];self.starts=[];y=8;max_width=0
        self.canvas.delete('all');self.images.clear()
        self.tiles.reset()
        for n,(w,h) in enumerate(self._sizes):
            if self.rotations.get(str(n),0)%180:w,h=h,w
            w=max(1,round(w*self.zoom/75));h=max(1,round(h*self.zoom/75))
            slot=self.canvas.create_rectangle(8,y,w+8,y+h,fill='white',outline='#aaa')
            self.pages.append((y,w,h,slot));self.starts.append(y);y+=h+16;max_width=max(max_width,w)
        self.height=y;self.canvas.configure(scrollregion=(0,0,max_width+16,y))
        self._transition=[];budget=16*1024*1024
        for key,photo in previous:
            n,z,r,x0,y0,x1,y1=key
            if r!=self.rotations.get(str(n),0):continue
            factor=self.zoom/z;w=max(1,round(photo.width()*factor));h=max(1,round(photo.height()*factor))
            if w*h*4>budget:continue
            budget-=w*h*4
            im=ImageTk.getimage(photo).resize((w,h),Image.Resampling.BILINEAR)
            frame=ImageTk.PhotoImage(im,master=self.canvas);self._transition.append(frame)
            self.canvas.create_image(8+round(x0*factor),self.pages[n][0]+round(y0*factor),image=frame,anchor='nw',tags=('pdf-transition',))
        # Keep completed OCR as well as native text when changing scale/rotation.
        for n,data in (self.selection.pages.items() if self.selection.source==self.path else ()):
            if data['chars']:
                text_key=(n,data['rotation']);self._text_cache[text_key]=data['chars']
                for key,(photo,chars) in list(self._bitmap_cache.items()):
                    if (key[0],key[2])==text_key:self._bitmap_cache[key]=(photo,data['chars'])
        self.selection.reset(self.path)
        self.canvas.yview_moveto((self.pages[self.number][0]-8)/self.height)
        if not defer:self.render_visible()

    def schedule_visible(self):
        if self._pending is None:self._pending=self.after(16,self.render_visible)

    def render_visible(self):
        if self._pending is not None:
            self.after_cancel(self._pending);self._pending=None
        if not self.pages or not self.winfo_exists():return
        top=self.canvas.canvasy(0);bottom=top+max(1,self.canvas.winfo_height())
        # Keep only nearby pages as bitmaps; page positions remain in the canvas.
        visible=set(range(self.page_at(top-160),self.page_at(bottom+160)+1))
        for n in set(self.images)-visible:
            self.canvas.delete('image'+str(n));del self.images[n]
        self.tiles.update(visible)
        missing={n for n in visible-set(self.images) if not self.tiles.large(n)}
        for n in sorted(missing):
            key=(n,self.zoom,self.rotations.get(str(n),0))
            if key not in self._bitmap_cache:continue
            photo,chars=self._bitmap_cache[key];self._bitmap_cache.move_to_end(key)
            previous=self.selection.pages.get(n)
            if previous and previous['rotation']==key[2] and previous['chars']:chars=previous['chars'];self._bitmap_cache[key]=(photo,chars)
            self.images[n]=photo
            self.selection.pages[n]=dict(x=8,y=self.pages[n][0],w=photo.width(),h=photo.height(),chars=chars,rotation=key[2])
            self.canvas.create_image(8,self.pages[n][0],image=photo,anchor='nw',tags=('image'+str(n),))
        missing={n for n in visible-set(self.images) if not self.tiles.large(n)}
        for n in sorted(missing,key=lambda n:abs(self.pages[n][0]-top)):
            token=(self._epoch,n)
            if token not in self._requested:
                self._requested.add(token)
                self.renderer.page(self._generation,self._epoch,n,self.zoom,self.rotations.get(str(n),0))
        # The page containing the upper visible part is the current page for splitting/rotation.
        while len(self._text_cache)>16:self._text_cache.pop(next(iter(self._text_cache)))
        for n in list(self.selection.pages):
            if n not in visible and not any(k[0]==n for k in self._text_cache):self.selection.pages.pop(n,None)
        self.number=self.page_at(top+min(80,max(0,bottom-top-1)))
        self.update_label()
        self.selection.highlight()
        self.draw_quick()

    def set_quick_model(self,values,labels):
        from fast_preview import eligible
        values=eligible(values,labels)
        if values!=self.quick_values:
            self.quick_values=values;self.quick_anchors={};self.quick_changes={};self._quick_requested=False
            self.quick_notice.pack_forget()
            if values and self._sizes is not None and self.path is not None:
                self._quick_requested=True;self.renderer.locate(self._generation,values)

    def quick_field(self,key,value):
        from fast_preview import family
        from tkinter import font
        def fallback():
            self.quick_changes.pop(key,None);self.draw_quick();return False
        a=self.quick_anchors.get(key)
        if not a or '\n' in value or len(value)>80 or self.rotations.get(str(a['page']),0):return fallback()
        if a['page']>=len(self.pages):return fallback()
        fam=family(a['font'])
        if not fam:return fallback()
        size=max(1,round(a['size']*self.zoom/75));style=(fam,size,a['flags'])
        if style not in self._quick_fonts:self._quick_fonts[style]=font.Font(self.canvas,family=fam,size=-size,weight='bold' if a['flags']&16 else 'normal',slant='italic' if a['flags']&2 else 'roman')
        width=(a['rect'][2]-a['rect'][0])*self.pages[a['page']][1]
        if self._quick_fonts[style].measure(value)>width+.5:return fallback()
        if value==self.quick_values.get(key):self.quick_changes.pop(key,None)
        else:self.quick_changes[key]=value
        self.draw_quick();return True

    def draw_quick(self):
        from fast_preview import family
        from tkinter import font
        self.canvas.delete('quick-edit')
        if not self.quick_changes:self.quick_notice.pack_forget();return
        self.quick_notice.pack(fill='x',before=self.quick_area)
        for key,value in self.quick_changes.items():
            a=self.quick_anchors.get(key)
            if not a or a['page']>=len(self.pages) or self.rotations.get(str(a['page']),0):continue
            top,w,h,_=self.pages[a['page']];x0,y0,x1,y1=a['rect'];size=max(1,round(a['size']*self.zoom/75));style=(family(a['font']),size,a['flags'])
            if style not in self._quick_fonts:self._quick_fonts[style]=font.Font(self.canvas,family=style[0],size=-size,weight='bold' if a['flags']&16 else 'normal',slant='italic' if a['flags']&2 else 'roman')
            f=self._quick_fonts[style]
            if f.measure(value)>(x1-x0)*w+.5:continue
            self.canvas.create_rectangle(8+x0*w,top+y0*h,8+x1*w,top+y1*h,fill='white',outline='',tags='quick-edit')
            self.canvas.create_text(8+x0*w,top+(y0+y1)*h/2,text=value,anchor='w',font=f,fill='#bb2424',tags='quick-edit')

    def poll_renderer(self):
        self._render_poll=None
        try:
            # Bound main-thread work per tick too: bitmap transfer is one page.
            result=self.renderer.results.get_nowait()
        except queue.Empty:result=None
        if result is not None and result['generation']==self._generation:
            if result['op']=='error':self.selection.message.set(result['error'])
            elif result['op']=='open':
                self._sizes=result['sizes']
                if self._sizes:
                    self.render()
                    restore=getattr(self,'_restore_fraction',None)
                    if restore and restore[0]==self._generation:
                        page=min(restore[1],len(self.pages)-1);top,w,h,_=self.pages[page]
                        self.canvas.yview_moveto((top+restore[2]*h)/self.height);self.render_visible()
                    self._restore_fraction=None
                    if self.quick_values and not self._quick_requested:
                        self._quick_requested=True;self.renderer.locate(self._generation,self.quick_values)
                else:self.page_text.set('Пустой PDF')
            elif result['op']=='locate':self.quick_anchors=result['anchors']
            elif result['op']=='overview':self.tiles.overview(result)
            elif result['op']=='tile' and result['epoch']==self._epoch:self.tiles.receive(result)
            elif result['op']=='page' and result['epoch']==self._epoch:
                n=result['page'];self._requested.discard((self._epoch,n));key=(n,result['zoom'],result['rotation'])
                image=Image.frombytes('RGB',result['size'],result['rgb']);photo=ImageTk.PhotoImage(image,master=self.canvas);image.close()
                chars=self._text_cache.get((n,key[2])) or result['chars'];self._text_cache[(n,key[2])]=chars
                self._bitmap_cache[key]=(photo,chars);self._bitmap_bytes+=photo.width()*photo.height()*4
                while self._bitmap_bytes>48*1024*1024 and self._bitmap_cache:
                    _,(old,_)=self._bitmap_cache.popitem(last=False);self._bitmap_bytes-=old.width()*old.height()*4
                self.images[n]=photo;self.selection.pages[n]=dict(x=8,y=self.pages[n][0],w=photo.width(),h=photo.height(),chars=chars,rotation=key[2])
                self.canvas.delete('image'+str(n));self.canvas.create_image(8,self.pages[n][0],image=photo,anchor='nw',tags=('image'+str(n),))
                self.canvas.delete('pdf-transition');self._transition=[]
                self.render_visible()
        if self.winfo_exists():self._render_poll=self.after(16,self.poll_renderer)
