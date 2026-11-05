"""Compare immediate scroll frames with settled frames on generated controls."""
import time
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab, ImageChops
from ui_surface import install_repaint

cursor = wintypes.POINT()
ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor))
ctypes.windll.user32.SetCursorPos(0, 0)
root = tk.Tk()
root.geometry('650x600+200+100')
canvas = tk.Canvas(root, highlightthickness=0)
canvas.pack(fill='both', expand=True)
inner = tk.Frame(canvas)
item = canvas.create_window(0, 0, window=inner, anchor='nw')
paint = install_repaint(canvas, inner)
canvas.configure(yscrollcommand=lambda *args: paint())
inner.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')), add='+')
canvas.bind('<Configure>', lambda event: canvas.itemconfigure(item, width=event.width), add='+')
variables = []
for index in range(100):
    label = tk.Label(inner, text=f'Field {index}', font=('Times New Roman', 12))
    label.pack(fill='x')
    value = tk.StringVar(value=f'Value {index}')
    variables.append(value)
    ttk.Combobox(inner, textvariable=value, font=('Times New Roman', 12)).pack(fill='x')
root.update()

def frame():
    root.update_idletasks()
    x, y = canvas.winfo_rootx(), canvas.winfo_rooty()
    return ImageGrab.grab(bbox=(x, y, x+canvas.winfo_width(), y+canvas.winfo_height()))

try:
    for family in ('Times New Roman', 'Segoe UI'):
        for widget in inner.winfo_children():
            widget.configure(font=(family, 12))
        root.update()
        positions = (0, 1, .25, .75, .5)
        reference = {}
        for position in positions:
            canvas.yview_moveto(position)
            root.update()
            time.sleep(.1)
            reference[position] = frame()
        started = time.monotonic()
        for cycle in range(40):
            position = positions[cycle % len(positions)]
            canvas.yview_moveto(position)
            actual = frame()
            difference = ImageChops.difference(reference[position], actual).getbbox()
            assert difference is None, (family, cycle, difference)
        assert all(value.get() == f'Value {index}' for index, value in enumerate(variables))
        print(f'PASS {family}: 40 immediate scroll frames, {time.monotonic()-started:.2f}s', flush=True)
finally:
    root.destroy()
    ctypes.windll.user32.SetCursorPos(cursor.x, cursor.y)
