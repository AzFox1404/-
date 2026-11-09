"""Compare immediate scroll frames with settled frames on generated controls."""
import time
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab, ImageChops
from form_surface import FormSurface

root = tk.Tk()
root.geometry('650x600+200+100')
canvas = tk.Canvas(root, highlightthickness=0)
canvas.pack(fill='both', expand=True)
inner = tk.Frame(canvas)
surface = FormSurface(canvas, inner, lambda *args: None,
                      lambda: dict(paper='#fffdfa', line='#d7cbc2', text='#222222'))
canvas.form_surface = surface
variables = []
for index in range(100):
    label = tk.Label(inner, text=f'Field {index}', font=('Times New Roman', 12))
    label.pack(fill='x')
    value = tk.StringVar(value=f'Value {index}')
    variables.append(value)
    ttk.Combobox(inner, textvariable=value, values=('One', 'Two'), font=('Times New Roman', 12)).pack(fill='x')
root.update()

def capture():
    image = ImageGrab.grab(window=canvas.winfo_id())
    assert any(low != high for low, high in image.getextrema()), 'blank form capture'
    return image

def frame():
    root.update_idletasks()
    return capture()

try:
    for family in ('Times New Roman', 'Segoe UI'):
        for widget in inner.winfo_children():
            widget.configure(font=(family, 12))
        surface.request_layout()
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
    active = next(iter(surface.editors))
    canvas.yview_moveto(0)
    surface.activate(active)
    active.focus_force()
    active.selection_range(0, 3)
    root.update()
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
            immediate = capture()
            canvas.event_generate('<Expose>')
            root.update_idletasks()
            settled = capture()
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
    assert root.focus_get() is active and active.selection_present()
    assert counts['events'] > 500 and counts['frames'] > 30, counts
    assert snapshots and not any(snapshots), snapshots
    assert max(gaps) < .5, max(gaps)
    assert all(value.get() == f'Value {index}' for index, value in enumerate(variables))
    print('PASS continuous reversing wheel', counts, 'worst heartbeat ms', round(max(gaps)*1000), flush=True)

    # Finish the last scheduled wheel step before starting the click scenario.
    root.after(120, root.quit)
    root.mainloop()
    items = canvas.find_withtag('form-row')
    fields = list(surface.editors)
    variables[1].set('Changed value')
    assert canvas.itemcget(surface.rows[fields[1]][4], 'text') == 'Changed value'
    assert canvas.find_withtag('form-row') == items
    canvas.yview_moveto(0)
    root.update()
    x, y, width, height, *_ = surface.rows[fields[1]]
    def pointer(sequence, x, y, state=0):
        canvas.event_generate(sequence, x=x, y=y, state=state,
                              rootx=canvas.winfo_rootx()+x, rooty=canvas.winfo_rooty()+y)

    pointer('<Motion>', x+width-10, y+height//2)
    pointer('<ButtonPress-1>', x+width-10, y+height//2)
    root.update()
    assert surface.active is fields[1] and fields[1].winfo_ismapped(), (surface.active, errors)
    popdown = root.tk.call('ttk::combobox::PopdownWindow', str(fields[1]))
    assert int(root.tk.call('winfo', 'ismapped', popdown))
    root.tk.call('ttk::combobox::Unpost', str(fields[1]))
    fields[1].focus_force()
    fields[1].event_generate('<Tab>')
    root.update()
    assert surface.active is fields[2] and root.focus_get() is fields[2]
    fields[2].event_generate('<Shift-Tab>')
    root.update()
    assert surface.active is fields[1] and root.focus_get() is fields[1]
    x, y, _, height, *_ = surface.rows[fields[2]]
    pointer('<Motion>', x+4, y+height//2)
    pointer('<ButtonPress-1>', x+4, y+height//2)
    pointer('<B1-Motion>', x+55, y+height//2, state=256)
    pointer('<ButtonRelease-1>', x+55, y+height//2)
    root.update()
    assert surface.active is fields[2] and fields[2].selection_present()
    canvas.yview_moveto(1)
    root.update()
    assert canvas.find_withtag('form-row') == items
    assert sum(field.winfo_ismapped() for field in fields) == 1
    assert not errors, errors
    print('PASS only changed value updates; dropdown and bidirectional Tab', flush=True)

finally:
    root.destroy()
