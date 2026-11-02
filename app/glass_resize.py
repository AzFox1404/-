"""One fixed glass canvas per drag; never move native child windows mid-drag."""
import ctypes as C
from ctypes import wintypes as W
import tkinter as tk
from PIL import Image,ImageFilter,ImageTk,ImageDraw

def capture(widget):
    w,h=widget.winfo_width(),widget.winfo_height()
    if w<2 or h<2:return None
    u=C.windll.user32;g=C.windll.gdi32
    u.GetDC.argtypes=[W.HWND];u.GetDC.restype=W.HDC;u.ReleaseDC.argtypes=[W.HWND,W.HDC]
    g.CreateCompatibleDC.argtypes=[W.HDC];g.CreateCompatibleDC.restype=W.HDC
    g.CreateCompatibleBitmap.argtypes=[W.HDC,C.c_int,C.c_int];g.CreateCompatibleBitmap.restype=W.HBITMAP
    g.SelectObject.argtypes=[W.HDC,W.HGDIOBJ];g.SelectObject.restype=W.HGDIOBJ
    g.DeleteObject.argtypes=[W.HGDIOBJ];g.DeleteDC.argtypes=[W.HDC]
    class INFO(C.Structure):
        _fields_=[('size',W.DWORD),('width',C.c_long),('height',C.c_long),('planes',W.WORD),('bits',W.WORD),('compression',W.DWORD),('image_size',W.DWORD),('xp',C.c_long),('yp',C.c_long),('used',W.DWORD),('important',W.DWORD)]
    g.GetDIBits.argtypes=[W.HDC,W.HBITMAP,W.UINT,W.UINT,C.c_void_p,C.c_void_p,W.UINT]
    dc=u.GetDC(widget.winfo_id());mem=g.CreateCompatibleDC(dc);bitmap=g.CreateCompatibleBitmap(dc,w,h);old=g.SelectObject(mem,bitmap)
    try:
        g.BitBlt.argtypes=[W.HDC,C.c_int,C.c_int,C.c_int,C.c_int,W.HDC,C.c_int,C.c_int,W.DWORD]
        if not g.BitBlt(mem,0,0,w,h,dc,0,0,0x00cc0020):return None
        info=INFO();info.size=C.sizeof(info);info.width=w;info.height=-h;info.planes=1;info.bits=32
        g.SelectObject(mem,old)
        data=C.create_string_buffer(w*h*4)
        if not g.GetDIBits(mem,bitmap,0,h,data,C.byref(info),0):return None
        return Image.frombuffer('RGB',(w,h),data,'raw','BGRX',0,1).copy()
    finally:
        g.SelectObject(mem,old);g.DeleteObject(bitmap);g.DeleteDC(mem);u.ReleaseDC(widget.winfo_id(),dc)

def install(split,app):
    if getattr(split,'_glass_drag',False):return
    split._glass_drag=True;split.configure(sashwidth=3,sashpad=0,showhandle=False,borderwidth=0,relief='flat',sashrelief='flat',proxyrelief='flat',proxyborderwidth=0,opaqueresize=False)
    state={'covers':[],'cards':[],'index':None,'target':None,'paint':None,'line':None,'grab':None,'focus':None,'reveal_timer':None,'reveal_now':None,'routed':[]};split.glass_state=state
    drag_tag='GlassDrag'+str(id(split))
    horizontal=str(split.cget('orient'))=='horizontal'
    def finish(event=None,commit=False):
        if state['index'] is None:return
        if state['paint'] is not None:split.after_cancel(state['paint']);state['paint']=None
        split.proxy_forget()
        if commit and state['target'] is not None:
            x,y=split.sash_coord(state['index'])
            split.sash_place(state['index'],state['target'] if horizontal else x,y if horizontal else state['target'])
        try:
            if split.grab_current() is split:split.grab_release()
            if state['grab'] is not None and state['grab'].winfo_exists():state['grab'].grab_set()
        except tk.TclError:pass
        for widget,tags in state['routed']:
            if widget.winfo_exists():widget.bindtags(tags)
        state['routed']=[]
        try:
            if state['focus'] is not None and state['focus'].winfo_exists() and state['focus'].winfo_viewable():state['focus'].focus_set()
        except tk.TclError:pass
        state['index']=None
        covers=list(state['covers']);line=state['line']
        # Keep PhotoImages alive until the glass is actually removed, otherwise
        # the last frame goes blank while Tk commits the real pane geometry.
        for cover in covers:cover.retiring_photos=[card.get('photo') for card in state['cards']]
        state['covers']=[];state['cards']=[];state['line']=None
        def reveal():
            state['reveal_timer']=None;state['reveal_now']=None
            for cover in covers:
                if cover.winfo_exists():cover.destroy()
            if line is not None and line.winfo_exists():line.destroy()
            if split.winfo_exists():
                # One complete invalidation after committing the sash: do not
                # retain pixels copied from the now-destroyed glass cover.
                u=C.windll.user32;u.RedrawWindow.argtypes=[W.HWND,C.c_void_p,W.HRGN,W.UINT]
                u.RedrawWindow(split.winfo_id(),None,None,0x185)
        state['reveal_now']=reveal
        if split.winfo_exists():state['reveal_timer']=split.after(24,reveal)
        else:reveal()
        return 'break'
    def paint():
        state['paint']=None
        if state['index'] is None:return
        idx=state['index'];target=state['target'];gap=3
        overlay=state['covers'][0]
        for n,card in enumerate(state['cards']):
            x,y,w,h=card['rect']
            if n==idx:
                if horizontal:w=target-x
                else:h=target-y
            elif n==idx+1:
                if horizontal:w=x+w-target-gap;x=target+gap
                else:h=y+h-target-gap;y=target+gap
            w=max(1,w);h=max(1,h)
            if card.get('last')==(x,y,w,h):continue
            card['last']=(x,y,w,h)
            im=card['image'].resize((w,h),Image.Resampling.BILINEAR)
            mask=Image.new('L',(w,h),0);ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=6,fill=255)
            rounded=Image.new('RGB',(w,h),app.colors['bg']);rounded.paste(im,mask=mask)
            d=ImageDraw.Draw(rounded);d.rounded_rectangle((0,0,w-1,h-1),radius=6,outline=app.colors['line'],width=1)
            if w>6 and h>14:
                edge=Image.blend(Image.new('RGB',(1,1),app.colors['glass']),Image.new('RGB',(1,1),'white'),.08).getpixel((0,0))
                d.rounded_rectangle((1,1,w-2,h-2),radius=6,outline=edge,width=1)
            card['photo']=ImageTk.PhotoImage(rounded,master=overlay)
            overlay.itemconfigure(card['item'],image=card['photo']);overlay.coords(card['item'],x,y)
        overlay.delete('divider')
        length=max(1,(split.winfo_height() if horizontal else split.winfo_width())-12)
        if horizontal:
            overlay.create_line(target+1,6,target+1,length+4,fill=app.colors['accent'],width=2,capstyle='round',tags='divider')
        else:
            overlay.create_line(6,target+1,length+4,target+1,fill=app.colors['accent'],width=2,capstyle='round',tags='divider')
    def start(event):
        hit=split.identify(event.x,event.y)
        if not hit:return
        if state['index'] is not None:finish()
        if state['reveal_now'] is not None:
            if state['reveal_timer'] is not None:split.after_cancel(state['reveal_timer'])
            state['reveal_now']();split.update_idletasks()
        idx=int(hit[0]);state['index']=idx;state['target']=split.sash_coord(idx)[0 if horizontal else 1];state['grab']=split.grab_current();state['focus']=split.focus_get()
        def protect(widget):
            state['routed'].append((widget,widget.bindtags()))
            widget.bindtags((drag_tag,)+widget.bindtags())
            for child in widget.winfo_children():protect(child)
        try:
            for name in split.panes():protect(split.nametowidget(str(name)))
            # Capture input before taking snapshots. A fast mouse-up may already
            # be queued for an underlying Entry/Treeview before covers are mapped.
            split.focus_set();split.grab_set()
            # Capture all panes before mapping one opaque backing. Its native
            # rectangle stays fixed; only canvas image items move. The backing
            # covers the old sash too, including rounded-card corner gaps.
            snapshots=[]
            for name in split.panes():
                pane=split.nametowidget(str(name))
                try:im=capture(pane)
                except (OSError,tk.TclError):im=None
                if im is None:im=Image.new('RGB',(pane.winfo_width(),pane.winfo_height()),app.colors['glass'])
                im=Image.blend(im.filter(ImageFilter.GaussianBlur(1.15)),Image.new('RGB',im.size,app.colors['glass']),.27)
                im=Image.blend(im,Image.new('RGB',im.size,'black'),.045)
                snapshots.append((pane,im))
            cover=tk.Canvas(split,bd=0,highlightthickness=0,takefocus=False,bg=app.colors['bg'])
            route(cover);cover.place(x=0,y=0,relwidth=1,relheight=1)
            state['covers']=[cover];state['line']=cover
            for pane,im in snapshots:
                state['cards'].append(dict(item=cover.create_image(0,0,anchor='nw'),image=im,rect=(pane.winfo_x(),pane.winfo_y(),pane.winfo_width(),pane.winfo_height())))
            paint()
        except Exception:
            finish()
            raise
        return 'break'
    def motion(event):
        if state['index'] is None:return
        idx=state['index'];cards=state['cards'];axis=0 if horizontal else 1;size=2 if horizontal else 3
        panes=list(split.panes());minimum=int(split.panecget(panes[idx],'minsize'));other=int(split.panecget(panes[idx+1],'minsize'))
        lo=cards[idx]['rect'][axis]+minimum
        hi=cards[idx+1]['rect'][axis]+cards[idx+1]['rect'][size]-other-3
        state['target']=max(lo,min(event.x if horizontal else event.y,hi))
        if state['paint'] is None:state['paint']=split.after(16,safe_paint)
        return 'break'
    def safe_paint():
        try:paint()
        except Exception:
            finish()
            raise
    def translated(event):
        event.x=event.x_root-split.winfo_rootx();event.y=event.y_root-split.winfo_rooty()
        return event
    def released(event):
        if state['index'] is None:return
        try:motion(translated(event))
        except Exception:
            finish()
            raise
        return finish(event,True)
    def route(widget):
        # A local Tk grab still sends events to descendants beneath the pointer.
        # Overlay canvases therefore must forward real motion/release events.
        widget.bind('<B1-Motion>',lambda e:motion(translated(e)))
        widget.bind('<ButtonRelease-1>',released)
        widget.bind('<Escape>',finish)
    split.bind_class(drag_tag,'<B1-Motion>',lambda e:motion(translated(e)))
    split.bind_class(drag_tag,'<ButtonRelease-1>',released)
    split.bind_class(drag_tag,'<Escape>',finish)
    split.bind('<ButtonPress-1>',start)
    split.bind('<B1-Motion>',motion)
    split.bind('<ButtonRelease-1>',released)
    split.bind('<Escape>',finish,add='+')
    split.bind('<FocusOut>',lambda e:finish() if e.widget is split else None,add='+')
    split.bind('<Unmap>',lambda e:finish() if e.widget is split else None,add='+')
    def destroyed(event):
        if event.widget is not split:return
        finish()
        if state['reveal_now'] is not None:
            if state['reveal_timer'] is not None:split.after_cancel(state['reveal_timer'])
            state['reveal_now']()
    split.bind('<Destroy>',destroyed,add='+')
