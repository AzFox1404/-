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
    u.SendMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];u.SendMessageW.restype=C.c_ssize_t
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
        def maximize():window.state('normal' if window.state()=='zoomed' else 'zoomed')
        buttons=[]
        for symbol,command in [('×',close),*([('□',maximize),('—',window.iconify)] if isinstance(window,tk.Tk) else [])]:
            b=ttk.Button(bar,text=symbol,command=command,style='Window.TButton',width=3,takefocus=False);b.window_button=True;b.pack(side='right');buttons.append(b)
        def move(event):
            position=(event.x_root & 0xffff)|((event.y_root & 0xffff)<<16)
            u.ReleaseCapture();u.SendMessageW(hwnd(),0xA1,2,position)
        for target in (bar,label,bar.logo):
            target.bind('<ButtonPress-1>',move)
            target.bind('<Double-Button-1>',lambda e=None:maximize() if isinstance(window,tk.Tk) else None)
        bar.label=label;bar.buttons=buttons
        original=window.title
        if not getattr(window,'_caption_title_hook',False):
            def title(*args):
                result=original(*args);current=getattr(window,'app_caption',None)
                if current is not None and current.winfo_exists():current.label.configure(text=original())
                return result
            window.title=title;window._caption_title_hook=True
        def sync(event=None):
            if event is not None and event.widget is not window:return
            if not window.winfo_exists() or not bar.winfo_exists():return
            full=bool(window.attributes('-fullscreen'))
            if full:bar.pack_forget()
            elif not bar.winfo_manager():
                before=next((w for w in window.winfo_children() if w is not bar and w.winfo_manager()=='pack'),None)
                bar.pack(fill='x',**({'before':before} if before else {}))
            style=u.GetWindowLongPtrW(hwnd(),-16)
            if style & 0x00c00000:
                u.SetWindowLongPtrW(hwnd(),-16,style & ~0x00c00000)
                u.SetWindowPos(hwnd(),None,0,0,0,0,0x37)
            from ui_surface import rounded_frame
            rounded_frame(window)
            bar.label.configure(text=window.title())
        mapped=window.bind('<Map>',lambda e=None:window.after_idle(sync) if e is None or e.widget is window else None,add='+')
        resized=window.bind('<Configure>',sync,add='+');bar.sync=sync
        window._caption_bindings=[('<Map>',mapped),('<Configure>',resized)]
    bar.configure(bg=colors['accent']);bar.label.configure(bg=colors['accent'],fg=colors['text'])
    from command_icons import command_icon
    bar.feather=command_icon(window,'feather',colors['text']);bar.logo.configure(image=bar.feather,bg=colors['accent'])
    window.iconphoto(isinstance(window,tk.Tk),bar.feather)
    window.caption_theme=dict(dark=dark,dark_mode=True,native_colors=False,custom=True)
    bar.sync()
