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
    from interactions import Interactions
    app = Interactions()
    app.root = root
    app.form_canvas = canvas
    app.form_mouse(canvas)
    errors = []
    root.report_callback_exception = lambda *error: errors.append(str(error[1]))
    counts = {'events': 0, 'frames': 0}
    started = time.monotonic()
    previous = [started]
    gaps = []
    snapshots = []
    running = [True]

    def feed():
        if not running[0]:
            return
        elapsed = time.monotonic()-started
        # Keep the event queue occupied, reversing direction every 80ms.
        canvas.event_generate('<MouseWheel>', delta=120 if int(elapsed/.08)%2 else -120)
        counts['events'] += 1
        root.after(0, feed)

    def inspect_frame():
        if not running[0]:
            return
        now = time.monotonic()
        gaps.append(now-previous[0])
        previous[0] = now
        counts['frames'] += 1
        if counts['frames'] % 5 == 0:
            x, y = canvas.winfo_rootx(), canvas.winfo_rooty()
            box = (x, y, x+canvas.winfo_width(), y+canvas.winfo_height())
            immediate = ImageGrab.grab(bbox=box)
            # Repaint the SAME position to obtain a reference, without
            # servicing queued wheel/timer events.
            for child in inner.winfo_children():
                child.event_generate('<Expose>')
            inner.event_generate('<Expose>')
            canvas.event_generate('<Expose>')
            root.update_idletasks()
            settled = ImageGrab.grab(bbox=box)
            snapshots.append(ImageChops.difference(immediate, settled).getbbox())
        if now-started >= 12:
            running[0] = False
            root.quit()
        else:
            root.after(16, inspect_frame)

    root.after(0, feed)
    root.after(20, inspect_frame)
    root.mainloop()
    assert not errors, errors
    assert counts['events'] > 500 and counts['frames'] > 30, counts
    assert snapshots and not any(snapshots), snapshots
    assert max(gaps) < .5, max(gaps)
    assert all(value.get() == f'Value {index}' for index, value in enumerate(variables))
    print('PASS continuous reversing wheel', counts, 'worst heartbeat ms', round(max(gaps)*1000), flush=True)

    # Pending wheel movement must yield to explicit scrollbar navigation.
    canvas.yview_moveto(.5)
    root.update_idletasks()
    canvas.scroll_form_units(4)
    canvas.yview_moveto(.25)
    wanted = canvas.yview()
    root.update_idletasks()
    end = time.monotonic()+.05
    while time.monotonic()<end:
        root.update()
    assert canvas.yview() == wanted
    # Clamping is applied in event order, so reversal at an edge responds.
    canvas.yview_moveto(0)
    root.update_idletasks()
    canvas.scroll_form_units(-1000)
    canvas.scroll_form_units(1)
    end = time.monotonic()+.05
    while time.monotonic()<end:
        root.update()
    assert canvas.yview()[0] > 0
    canvas.scroll_form_units(1000)
    canvas.destroy()
    root.update()
    assert not errors, errors

finally:
    root.destroy()
    ctypes.windll.user32.SetCursorPos(cursor.x, cursor.y)
