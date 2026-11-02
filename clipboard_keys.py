"""Physical-key clipboard shortcuts independent of the Windows keyboard layout."""
import tkinter as tk


def operation(event):
    if not (event.state & 4) or event.state & (8|0x20000):return None
    return {67:'copy',86:'paste',88:'cut',65:'all',90:'undo',89:'redo'}.get(event.keycode)


def install(widget):
    if getattr(widget,'clipboard_keys_installed',False):
        tag='ClipboardKeys'+str(widget)
        widget.bindtags((tag,)+tuple(t for t in widget.bindtags() if t!=tag));return
    widget.clipboard_keys_installed=True
    tag='ClipboardKeys'+str(widget)
    widget.bindtags((tag,)+widget.bindtags())
    def key(event):
        op=operation(event)
        if op not in ('copy','paste','cut','all'):return
        readonly=str(widget.cget('state')) in ('readonly','disabled')
        if op=='all':widget.selection_range(0,'end');widget.icursor('end');return 'break'
        if op in ('copy','cut'):
            if widget.selection_present():
                text=widget.selection_get();widget.clipboard_clear();widget.clipboard_append(text)
                if op=='cut' and not readonly:widget.delete('sel.first','sel.last')
            return 'break'
        if not readonly:
            try:text=widget.clipboard_get()
            except tk.TclError:return 'break'
            if widget.selection_present():widget.delete('sel.first','sel.last')
            widget.insert('insert',text);widget.xview('insert')
        return 'break'
    widget.bind_class(tag,'<KeyPress>',key)
    def cleanup(event):
        if event.widget is widget:
            widget.unbind_class(tag,'<KeyPress>')
    widget.bind('<Destroy>',cleanup,add='+')
