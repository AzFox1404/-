import tkinter as tk,json
from tkinter import ttk
from pathlib import Path
root=tk.Tk();root.title('Проверка клавиш Бюро ИД');root.geometry('650x300+100+100')
log=Path('review/key-events.jsonl');log.write_text('','utf-8')
def event(e):
 with log.open('a',encoding='utf-8') as f:f.write(json.dumps(dict(keycode=e.keycode,keysym=e.keysym,state=e.state,char=e.char),ensure_ascii=False)+'\n')
root.bind_class('KeyDebug','<KeyPress>',event)
a=ttk.Entry(root);a.pack(fill='x',padx=20,pady=20);a.insert(0,'Проверка 869');a.bindtags(('KeyDebug',)+a.bindtags());a.focus_force();a.selection_range(0,'end')
b=ttk.Entry(root);b.pack(fill='x',padx=20,pady=20);b.bindtags(('KeyDebug',)+b.bindtags())
status=tk.StringVar();ttk.Label(root,textvariable=status).pack()
def poll():
 try:clip=root.clipboard_get()
 except tk.TclError:clip=''
 status.set('Источник: '+a.get()+' | Поле: '+b.get()+' | Буфер: '+clip[:80]);root.after(200,poll)
poll();root.after(180000,root.destroy);root.mainloop()
