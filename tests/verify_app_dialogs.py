"""Exercise real themed modals without Office or private templates."""
import tempfile,tkinter as tk
from tkinter import ttk
from pathlib import Path
import studio
from app_dialogs import messagebox,simpledialog

def children(w):
    for child in w.winfo_children():
        yield child
        yield from children(child)

with tempfile.TemporaryDirectory() as td:
    base=Path(td);studio.STORE=base/'store';studio.PROJECTS=studio.STORE/'Проекты'
    studio.LIB=studio.STORE/'Библиотека/Шаблоны';studio.SAMPLES=base/'missing/sample'
    root=tk.Tk();app=studio.Studio(root);errors=[]
    def report(*e):
        errors.append(str(e[1]));__import__('traceback').print_exception(*e);root.after_idle(root.destroy)
    root.report_callback_exception=report
    def answer(text=None,label='Применить'):
        win=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and w.winfo_exists())
        if not win.winfo_viewable():root.after(25,lambda:answer(text,label));return
        assert str(win.transient())==str(root)
        buttons=[w for w in children(win) if isinstance(w,ttk.Button) and not getattr(w,'window_button',False)]
        assert buttons and all(w.cget('image') and w.cget('style')=='Compact.TButton' for w in buttons)
        assert all(w.cget('text') not in ('OK','Cancel') for w in buttons)
        if text is not None:
            entry=next(w for w in children(win) if isinstance(w,ttk.Entry));entry.delete(0,'end');entry.insert(0,text)
        next(w for w in buttons if w.cget('text')==label).invoke()
    root.update()
    for dark in (False,True):
        app.dark=dark;app.set_palette();app.paint(root)
        root.after(70,lambda:answer('3'))
        assert simpledialog.askinteger('Добавление','Количество строк:',parent=root)==3
        root.after(70,lambda:answer(label='Нет'))
        assert messagebox.askyesno('Удаление','Удалить раздел?',parent=root) is False
    root.attributes('-fullscreen',True);root.update()
    root.after(70,lambda:answer(label='Понятно'))
    assert messagebox.showinfo('Готово','Длинное сообщение. '*80,parent=root) is True
    root.after(70,lambda:answer(label='Отмена'))
    assert simpledialog.askstring('Название','Название раздела:',parent=root) is None
    root.attributes('-fullscreen',False)
    buttons=[w for w in children(app.landing) if isinstance(w,ttk.Button) and w.cget('text') not in ('—','□','↗')]
    assert buttons and all(w.cget('image') and w.cget('style')=='Compact.TButton' for w in buttons)
    root.destroy();assert not errors,errors
print('PASS Russian compact icon dialogs, numeric input, cancellation, both themes, fullscreen owner, home actions')
