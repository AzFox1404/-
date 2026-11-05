"""Application-painted captions with native resizing, movement and taskbar identity."""
import tkinter as tk
from tkinter import ttk
import ctypes as C
from ctypes import wintypes as W

def install(window,colors,dark):
    if window.overrideredirect():return
    u=C.WinDLL('user32')
    u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND
    u.GetWindowLongPtrW.argtypes=[W.HWND,C.c_int];u.GetWindowLongPtrW.restype=C.c_ssize_t
    u.SetWindowLongPtrW.argtypes=[W.HWND,C.c_int,C.c_ssize_t]
    u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
    u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];u.PostMessageW.restype=W.BOOL
    def hwnd():return u.GetParent(window.winfo_id()) or window.winfo_id()
    bar=getattr(window,'app_caption',None)
    if bar is None or not bar.winfo_exists():
        for event,binding in getattr(window,'_caption_bindings',[]):window.unbind(event,binding)
        bar=tk.Frame(window,height=28);bar.tone='accent';bar.native_caption=True;window.app_caption=bar
        from command_icons import command_icon
        bar.feather=command_icon(window,'feather',colors['text'])
        bar.logo=tk.Label(bar,image=bar.feather,bd=0,padx=6);bar.logo.tone='accent';bar.logo.pack(side='left')
        label=tk.Label(bar,text=window.title(),anchor='w',padx=6,font=('Segoe UI',9));label.tone='accent';label.pack(side='left',fill='x',expand=True)
        def close():
            command=window.protocol('WM_DELETE_WINDOW')
            if command:window.tk.eval(command)
            else:window.destroy()
        def maximize():
            if all(map(int,window.resizable())):
                window.state('normal' if window.state()=='zoomed' else 'zoomed')
        buttons=[]
        for symbol,command in [('×',close),*([('□',maximize),('—',window.iconify)] if isinstance(window,tk.Tk) else [])]:
            b=ttk.Button(bar,text=symbol,command=command,style='Window.TButton',width=3,takefocus=False);b.window_button=True;b.pack(side='right');buttons.append(b)
        def move(event):
            # Enter the native move loop only after Tk returns from this callback.
            position=(event.x_root & 0xffff)|((event.y_root & 0xffff)<<16)
            u.ReleaseCapture();u.PostMessageW(hwnd(),0xA1,2,position)
            return 'break'
        for target in (bar,label,bar.logo):
            target.bind('<ButtonPress-1>',move)
            target.bind('<Double-Button-1>',lambda e:(maximize(),'break')[1])
        bar.label=label;bar.buttons=buttons
        original=window.title
        if not getattr(window,'_caption_title_hook',False):
            def title(*args):
                result=original(*args);current=getattr(window,'app_caption',None)
                if current is not None and current.winfo_exists():current.label.configure(text=original())
                return result
            window.title=title;window._caption_title_hook=True
        bar.pending=None;bar.syncing=False
        def sync(event=None):
            if event is not None and event.widget is not window:return
            if not window.winfo_exists() or not bar.winfo_exists():return
            if bar.syncing:return
            bar.syncing=True
            try:apply_frame()
            finally:bar.syncing=False
        def apply_frame():
            # A withdrawn/unmapped Tk window may still have its temporary
            # wrapper. Never install a clipping region on that surface.
            if not window.winfo_ismapped():return
            full=bool(window.attributes('-fullscreen'))
            if full:bar.pack_forget()
            elif not bar.winfo_manager():
                before=next((w for w in window.winfo_children() if w is not bar and w.winfo_manager()=='pack'),None)
                bar.pack(fill='x',**({'before':before} if before else {}))
            handle=u.GetParent(window.winfo_id())
            if not handle:return
            style=u.GetWindowLongPtrW(handle,-16)
            wanted=style & ~0x00c00000
            if not full and not getattr(window,'_close_only',False) and all(map(int,window.resizable())):
                wanted|=0x00090000
            if wanted!=style:
                u.SetWindowLongPtrW(hwnd(),-16,wanted)
                u.SetWindowPos(hwnd(),None,0,0,0,0,0x37)
            from ui_surface import rounded_frame
            rounded_frame(window)
            if bar.label.cget('text')!=window.title():bar.label.configure(text=window.title())
        def schedule(event=None):
            if event is not None and event.widget is not window:return
            if bar.pending is None:
                def flush():
                    bar.pending=None;sync()
                # Tk may recreate its wrapper and restore native styles while
                # applying transient/state/Map. Reconcile after that operation.
                bar.pending=window.after_idle(flush)
        mapped=window.bind('<Map>',schedule,add='+')
        resized=window.bind('<Configure>',schedule,add='+');bar.sync=schedule;bar.reconcile=sync
        def dispose(e):
            if e.widget is window and bar.pending is not None:
                window.after_cancel(bar.pending);bar.pending=None
        window.bind('<Destroy>',dispose,add='+')
        window._caption_bindings=[('<Map>',mapped),('<Configure>',resized)]
    bar.configure(bg=colors['accent']);bar.label.configure(bg=colors['accent'],fg=colors['text'])
    from command_icons import command_icon
    bar.feather=command_icon(window,'feather',colors['text']);bar.logo.configure(image=bar.feather,bg=colors['accent'])
    # Reapplying iconphoto during every paint can recreate the Windows wrapper.
    if not getattr(window,'_caption_icon_set',False):
        window.iconphoto(isinstance(window,tk.Tk),bar.feather);window._caption_icon_set=True
    window.caption_theme=dict(dark=dark,dark_mode=True,native_colors=False,custom=True)
    bar.sync()
