"""Shared Russian modal dialogs. Native file pickers stay with Windows."""
import tkinter as tk
from tkinter import ttk
import weakref

_app = None

def configure(app):
    global _app
    _app = weakref.ref(app)

def place_window(app,win,settle=False):
    """Center new app windows; nested dialogs cascade toward ten o'clock."""
    if not win.winfo_exists() or getattr(win,'_placed',False) and not settle:return
    if settle:
        x,y=getattr(win,'_placement_position',(None,None))
        if (win.winfo_x(),win.winfo_y())!=(x,y):return
    root=app.root
    if not root.winfo_viewable():return
    def descendants(parent):
        for child in parent.winfo_children():
            if isinstance(child,tk.Toplevel):yield child
            yield from descendants(child)
    floating=set(getattr(app,'windows',{}).values())
    depth=sum(1 for w in descendants(root) if w is not win and w not in floating and w.winfo_viewable() and not w.overrideredirect())
    if settle:depth=getattr(win,'_placement_depth',depth)
    width=max(win.winfo_width(),win.winfo_reqwidth());height=max(win.winfo_height(),win.winfo_reqheight())
    if hasattr(win,'_placement_size') and not settle:width,height=win._placement_size
    x=root.winfo_rootx()+(root.winfo_width()-width)//2-depth*24
    y=root.winfo_rooty()+(root.winfo_height()-height)//2-depth*16
    win._placed=True;win.geometry(f'{x:+d}{y:+d}' if settle else f'{width}x{height}{x:+d}{y:+d}')
    win._placement_position=(x,y);win._placement_depth=depth
    if not settle:win.after(50,lambda:place_window(app,win,True))

def action(app,parent,text,key,command):
    button=ttk.Button(parent,text=text,image=app.icon(key),compound='left',
                      style='Compact.TButton',command=command)
    button.icon_name=key
    from hints import hover_icon
    hover_icon(button,app,key)
    return button

def modal(app,title,prompt,choices,parent=None,initial=None,validator=None):
    focus=app.root.focus_get()
    owner=(parent or focus or app.root).winfo_toplevel()
    win=tk.Toplevel(owner);win.withdraw();win.title(title);win.transient(owner)
    win.geometry('500x200' if initial is not None else '500x170');win.minsize(440,170)
    result=[None];ready=[False]
    row=ttk.Frame(win);row.pack(side='bottom',fill='x',padx=12,pady=10)
    buttons=ttk.Frame(row);buttons.pack(side='right')
    if len(prompt)>500:
        body=ttk.Frame(win);body.pack(fill='both',expand=True,padx=16,pady=12)
        area=tk.Text(body,wrap='word',height=12,width=58,bd=0)
        scroll=ttk.Scrollbar(body,command=area.yview);scroll.pack(side='right',fill='y')
        area.configure(yscrollcommand=scroll.set);area.pack(fill='both',expand=True)
        area.insert('1.0',prompt);area.configure(state='disabled',bg=app.colors['bg'],fg=app.colors['text'])
        win.geometry('500x360')
    else:ttk.Label(win,text=prompt,padding=16,wraplength=465).pack(fill='x')
    entry=None
    if initial is not None:
        value=tk.StringVar(value=initial)
        entry=ttk.Entry(win,textvariable=value);entry.pack(fill='x',padx=16)
        error=ttk.Label(win,text='',wraplength=465);error.pack(fill='x',padx=16)
    previous=owner.grab_current()
    def finish(answer):
        if not ready[0]:return
        if not win.winfo_exists():return
        if entry is not None and answer is True:
            try:answer=validator(value.get()) if validator else value.get()
            except ValueError as exc:error.configure(text=str(exc));entry.focus_set();return
        result[0]=answer;win.grab_release();win.destroy()
        if previous is not None and previous.winfo_exists():previous.grab_set()
    for text,key,answer in choices:
        action(app,buttons,text,key,lambda v=answer:finish(v)).pack(side='left',padx=3)
    win.protocol('WM_DELETE_WINDOW',lambda:finish(None))
    win.bind('<Escape>',lambda e:finish(None))
    win.bind('<Return>',lambda e:finish(choices[0][2]))
    app.paint(win);win.update_idletasks()
    if not win.winfo_exists():return result[0]
    width=max(500,buttons.winfo_reqwidth()+30)
    height=max(win.winfo_height(),win.winfo_reqheight()+12)
    win.geometry(f'{width}x{height}')
    win._placement_size=(width,height)
    place_window(app,win)
    win.deiconify();win.grab_set();win.lift()
    ready[0]=True
    if entry is not None:entry.focus_set();entry.selection_range(0,'end')
    else:buttons.winfo_children()[0].focus_set()
    app.root.wait_window(win)
    return result[0]

def ask_text(app,title,prompt,initial=''):
    return modal(app,title,prompt,[('Применить','save',True),('Отмена','undo',None)],initial=initial)

class Messages:
    def _show(self,title,message,choices,parent=None,**kwargs):
        app=_app() if _app else None
        if app is None:raise RuntimeError('Диалоги приложения ещё не настроены')
        return modal(app,title,message,choices,parent=parent)
    def showinfo(self,title,message,**kwargs):
        return self._show(title,message,[('Понятно','checkall',True)],**kwargs)
    showwarning=showinfo
    showerror=showinfo
    def askyesno(self,title,message,**kwargs):
        return self._show(title,message,[('Да','checkall',True),('Нет','close',False)],**kwargs) is True
    def askyesnocancel(self,title,message,**kwargs):
        return self._show(title,message,[('Да','checkall',True),('Нет','close',False),('Отмена','undo',None)],**kwargs)

class Inputs:
    def askstring(self,title,prompt,initialvalue='',parent=None,**kwargs):
        app=_app() if _app else None
        return modal(app,title,prompt,[('Применить','save',True),('Отмена','undo',None)],parent,initialvalue)
    def askinteger(self,title,prompt,initialvalue=1,minvalue=1,maxvalue=None,parent=None,**kwargs):
        def parse(text):
            try:value=int(text)
            except ValueError:raise ValueError('Введите целое число.')
            if value<minvalue or maxvalue is not None and value>maxvalue:
                raise ValueError(f'Введите число от {minvalue}'+(f' до {maxvalue}.' if maxvalue is not None else '.'))
            return value
        app=_app() if _app else None
        return modal(app,title,prompt,[('Применить','save',True),('Отмена','undo',None)],parent,str(initialvalue),parse)

messagebox=Messages()
simpledialog=Inputs()
