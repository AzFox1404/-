import tempfile,tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from tkinter import ttk
import studio

with tempfile.TemporaryDirectory() as td:
    p=Path(td);studio.STORE=p;studio.PROJECTS=p/'Проекты';studio.LIB=p/'Библиотека/Шаблоны'
    root=tk.Tk();app=studio.Studio(root)
    s=SimpleNamespace(analysis={'warnings':[]},spec={'titleClient':{'label':'ЗАКАЗЧИК: '},'other':{'label':'ЗАКАЗЧИК: '}})
    # Session identity is the dictionary key; use a small hashable stand-in.
    class Session:pass
    session=Session();session.analysis=s.analysis;session.spec=s.spec
    app.current=session;app.models={session:{'titleClient':'First','other':'Second'}};app.views={k:tk.StringVar(value=v) for k,v in app.models[session].items()}
    app.review_word_fields();root.update()
    win=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and w.title()=='Проверка распознанных полей')
    def descendants(w):
        for c in w.winfo_children():yield c;yield from descendants(c)
    choice=next(w for w in descendants(win) if isinstance(w,ttk.Combobox))
    assert all('titleClient' not in text and '[' not in text for text in choice.cget('values'))
    assert not any(isinstance(w,ttk.Button) and w.cget('text') for w in descendants(win))
    choice.current(1);choice.event_generate('<<ComboboxSelected>>');root.update()
    entry=next(w for w in descendants(win) if isinstance(w,ttk.Entry) and not isinstance(w,ttk.Combobox));entry.delete(0,'end');entry.insert(0,'New')
    button=next(w for w in descendants(win) if getattr(w,'hint_message','')=='Применить значение к выбранному полю')
    button.event_generate('<ButtonPress-1>',x=10,y=10);button.event_generate('<ButtonRelease-1>',x=10,y=10)
    assert app.views['other'].get()=='New' and app.views['titleClient'].get()=='First'
    app.current=None;root.destroy();print('PASS compact icon-only field review, no internal identifiers, duplicate human labels remain selectable')
