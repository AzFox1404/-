"""Draw the form on one canvas and mount its native editor on demand."""
import tkinter as tk
from tkinter import font, ttk

from PIL import Image, ImageDraw, ImageTk


class FormSurface:
    def __init__(self, canvas, editor_host, scrollbar, palette):
        self.canvas = canvas
        self.host = editor_host
        self.scrollbar = scrollbar
        self.palette = palette
        self.style = ttk.Style(canvas)
        self.layout = None
        self.editors = {}
        self.active = None
        self.pressed = None
        self.rows = {}
        self.images = {}
        self.fonts = {}
        self.refresh_job = None
        self.editor_job = None
        self.view = None
        self.wheel_job = None
        self.wheel_origin = None
        self.wheel_target = None
        canvas.configure(takefocus=True, yscrollcommand=self.scrolled)
        canvas.bind('<Configure>', self.request_layout, add='+')
        canvas.bind('<Destroy>', self.destroy, add='+')
        canvas.bind('<FocusIn>', self.enter_form, add='+')
        canvas.bind('<B1-Motion>', self.drag, add='+')
        canvas.bind('<ButtonRelease-1>', self.release, add='+')
        canvas.redraw_theme = self.request_layout
        self.request_layout()

    def request_layout(self, event=None):
        if self.refresh_job is None:
            self.refresh_job = self.canvas.after_idle(self.draw)

    def draw(self):
        self.refresh_job = None
        if self.layout is None:
            self.layout = [(widget, widget.pack_info()) for widget in self.host.pack_slaves()]
            for widget, options in self.layout:
                widget.pack_forget()
                if isinstance(widget, ttk.Entry):
                    widget.configure(takefocus=False)
                    widget.bind('<Tab>', lambda event: self.tab(1), add='+')
                    widget.bind('<Shift-Tab>', lambda event: self.tab(-1), add='+')
                    widget.bind('<FocusIn>', lambda event, field=widget: self.reveal(field), add='+')
                    name = str(widget.cget('textvariable'))
                    command = self.canvas.register(lambda *args, field=widget: self.update_value(field))
                    self.canvas.tk.call('trace', 'add', 'variable', name, 'write', command)
                    tag = f'field-{len(self.editors)}'
                    self.editors[widget] = (name, command, tag)
                    self.canvas.tag_bind(tag, '<ButtonPress-1>',
                                         lambda event, field=widget: self.click(event, field))
        canvas = self.canvas
        canvas.delete('form-row')
        self.rows.clear()
        self.images.clear()
        self.fonts.clear()
        colors = self.palette()
        y = 0
        width = max(1, canvas.winfo_width())
        for widget, options in self.layout:
            pad = options['pady']
            before, after = (pad, pad) if isinstance(pad, int) else map(int, pad)
            y += before
            height = widget.winfo_reqheight() + 2*int(options['ipady'])
            left = int(options['padx'])
            available = max(1, width-2*left)
            if widget in self.editors:
                self.draw_field(widget, left, y, available, height, colors)
            else:
                style = widget.cget('style') if isinstance(widget, ttk.Label) else ''
                face = widget.cget('font') or self.style.lookup(style or 'TLabel', 'font') or 'TkDefaultFont'
                wrap = widget.winfo_pixels(widget.cget('wraplength') or 0)
                inset = 10 if wrap else 0
                canvas.create_text(left+inset, y+height/2, anchor='w', text=widget.cget('text'),
                                   width=min(wrap, available) if wrap else 0,
                                   font=face, fill=colors['text'], tags='form-row')
            y += height + after
        canvas.configure(scrollregion=(0, 0, width, y))
        self.position_editor()

    def draw_field(self, widget, x, y, width, height, colors):
        canvas = self.canvas
        style = widget.cget('style') or widget.winfo_class()
        fill = self.style.lookup(style, 'fieldbackground') or colors['paper']
        foreground = self.style.lookup(style, 'foreground') or colors['text']
        key = (width, height, fill)
        if key not in self.images:
            background = tuple(value // 257 for value in canvas.winfo_rgb(canvas.cget('background')))
            image = Image.new('RGB', (width, height), background)
            surface = tuple(value // 257 for value in canvas.winfo_rgb(fill))
            ImageDraw.Draw(image).rounded_rectangle((0, 0, width-1, height-1), radius=5,
                                                     fill=surface, outline=colors['line'])
            self.images[key] = ImageTk.PhotoImage(image, master=canvas)
        tag = self.editors[widget][2]
        tags = ('form-row', tag)
        canvas.create_image(x, y, image=self.images[key], anchor='nw', tags=tags)
        combo = isinstance(widget, ttk.Combobox)
        if combo:
            ax, ay = x+width-12, y+height/2
            canvas.create_polygon(ax-4, ay-2, ax+4, ay-2, ax, ay+2, fill=foreground, tags=tags)
        face = str(widget.cget('font') or 'TkDefaultFont')
        if face not in self.fonts:
            self.fonts[face] = font.Font(canvas, font=face)
        text = canvas.create_text(x+8, y+height/2, anchor='w', font=self.fonts[face],
                                  fill=foreground, tags=tags)
        self.rows[widget] = (x, y, width, height, text, self.fonts[face], width-(30 if combo else 16))
        self.update_value(widget)

    def update_value(self, widget):
        if widget not in self.rows:
            return
        _, _, _, _, item, face, width = self.rows[widget]
        value = str(self.canvas.getvar(self.editors[widget][0])).replace('\n', ' ')
        low, high = 0, len(value)
        while low < high:
            middle = (low+high+1)//2
            if face.measure(value[:middle]) <= width:
                low = middle
            else:
                high = middle-1
        self.canvas.itemconfigure(item, text=value[:low])

    def wheel(self, units):
        canvas = self.canvas
        first, last = canvas.yview()
        region = canvas.tk.splitlist(canvas.cget('scrollregion'))
        if not region or last-first >= 1:
            return
        extent = float(region[3])
        step = int((last-first)*extent/10)/extent
        if self.wheel_origin != (first, last):
            self.wheel_origin = (first, last)
            self.wheel_target = first
        self.wheel_target = max(0., min(1-(last-first), self.wheel_target+units*step))
        if self.wheel_job is None:
            self.wheel_job = canvas.after(16, self.apply_wheel)

    def apply_wheel(self):
        self.wheel_job = None
        if self.canvas.yview() == self.wheel_origin:
            self.canvas.yview_moveto(self.wheel_target)
            # Present the canvas scroll before taking the next burst of input.
            self.canvas.update_idletasks()
        self.wheel_origin = None

    def scrolled(self, first, last):
        self.scrollbar(first, last)
        view = (first, last)
        if self.active is not None and self.view is not None and view != self.view:
            # Keep focus and selection in the same native editor, parked
            # outside the clip while the canvas is moving.
            if self.editor_job is None:
                self.host.place_configure(x=-self.host.winfo_width()-2)
            else:
                self.canvas.after_cancel(self.editor_job)
            self.editor_job = self.canvas.after(100, self.restore_editor)
        self.view = view

    def restore_editor(self):
        self.editor_job = None
        self.position_editor()

    def position_editor(self):
        if self.editor_job is None and self.active in self.rows:
            x, y, width, height, *_ = self.rows[self.active]
            self.host.place(x=x, y=round(y-self.canvas.canvasy(0)), width=width, height=height)
            self.host.lift()

    def activate(self, widget, focus=True):
        if self.editor_job is not None:
            self.canvas.after_cancel(self.editor_job)
            self.editor_job = None
        if self.active is not widget:
            self.pressed = None
            if self.active is not None:
                self.active.place_forget()
            self.active = widget
            widget.place(x=0, y=0, relwidth=1, relheight=1)
        self.position_editor()
        if focus:
            widget.focus_set()

    def click(self, event, widget):
        self.activate(widget)
        self.canvas.update_idletasks()
        self.pressed = widget
        self.forward_pointer(widget, event, '<ButtonPress-1>')
        # The original button press was on Canvas, so Windows can deliver
        # the rest of the drag to Canvas even after the editor is mounted.
        if isinstance(widget, ttk.Combobox):
            popup = widget.tk.call('ttk::combobox::PopdownWindow', str(widget))
            if int(widget.tk.call('winfo', 'ismapped', popup)):
                self.pressed = None

    def drag(self, event):
        if self.pressed is not None:
            self.forward_pointer(self.pressed, event, '<B1-Motion>')

    def release(self, event):
        widget, self.pressed = self.pressed, None
        if widget is not None:
            self.forward_pointer(widget, event, '<ButtonRelease-1>')

    def forward_pointer(self, widget, event, sequence):
        widget.event_generate(sequence, x=event.x_root-widget.winfo_rootx(),
                              y=event.y_root-widget.winfo_rooty(),
                              rootx=event.x_root, rooty=event.y_root, state=event.state)

    def enter_form(self, event):
        if self.editors:
            self.activate(self.active or next(iter(self.editors)))

    def reveal(self, widget):
        if widget not in self.rows:
            return
        _, y, _, height, *_ = self.rows[widget]
        top = self.canvas.canvasy(0)
        viewport = self.canvas.winfo_height()
        extent = float(self.canvas.tk.splitlist(self.canvas.cget('scrollregion'))[3])
        if y < top:
            self.canvas.yview_moveto(y/extent)
        elif y+height > top+viewport:
            self.canvas.yview_moveto((y+height-viewport)/extent)

    def tab(self, direction):
        fields = list(self.editors)
        index = fields.index(self.active)+direction
        if 0 <= index < len(fields):
            self.activate(fields[index])
        else:
            target = self.canvas.tk_focusNext() if direction > 0 else self.canvas.tk_focusPrev()
            if target is not None:
                target.focus_set()
        return 'break'

    def destroy(self, event):
        if event.widget is not self.canvas:
            return
        for job in (self.refresh_job, self.editor_job, self.wheel_job):
            if job is not None:
                self.canvas.after_cancel(job)
        for name, command, _ in self.editors.values():
            self.canvas.tk.call('trace', 'remove', 'variable', name, 'write', command)
