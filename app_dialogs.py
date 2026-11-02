"""The application's Russian text-entry dialog."""
import tkinter as tk
from tkinter import ttk

def ask_text(app,title,prompt,initial=''):
    win=tk.Toplevel(app.root);win.title(title);win.geometry('450x160');win.minsize(400,150)
    value=tk.StringVar(value=initial);result=[None]
    ttk.Label(win,text=prompt,padding=(14,10),wraplength=410).pack(anchor='w')
    entry=ttk.Entry(win,textvariable=value);entry.pack(fill='x',padx=14,ipady=3)
    actions=ttk.Frame(win);actions.pack(side='bottom',fill='x',padx=12,pady=10)
    def finish(accepted):
        if accepted:result[0]=value.get()
        win.grab_release();win.destroy()
    for text,key,accepted in [('Применить','save',True),('Отмена','close',False)]:
        ttk.Button(actions,text=text,image=app.icon(key),compound='left',style='Action.TButton',command=lambda ok=accepted:finish(ok)).pack(side='right',padx=3)
    win.protocol('WM_DELETE_WINDOW',lambda:finish(False))
    win.bind('<Return>',lambda e:finish(True));win.bind('<Escape>',lambda e:finish(False))
    app.paint(win);win.grab_set();entry.focus_set();entry.selection_range(0,'end')
    app.root.wait_window(win)
    return result[0]
