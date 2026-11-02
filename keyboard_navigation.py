"""Arrow navigation from toolbar/option focus without stealing text caret keys."""
import tkinter as tk
from tkinter import ttk

def install(window,navigate):
    def key(event):
        w=event.widget
        if isinstance(w,(tk.Entry,ttk.Entry,ttk.Combobox,tk.Text,tk.Listbox,ttk.Treeview,ttk.Spinbox)):return
        navigate(-1 if event.keysym=='Up' else 1)
        return 'break'
    window.bind('<Up>',key,add='+');window.bind('<Down>',key,add='+')
