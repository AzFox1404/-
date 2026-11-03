"""Physical-key clipboard shortcuts independent of the Windows keyboard layout."""
import tkinter as tk


def operation(event):
    if not (event.state & 4) or event.state & (8|0x20000):return None
    if event.keycode==90 and event.state&1:return 'redo'
    return {67:'copy',86:'paste',88:'cut',65:'all',90:'undo',89:'redo'}.get(event.keycode)


def install(widget):
    if getattr(widget,'clipboard_keys_installed',False):
        tag='ClipboardKeys'+str(widget)
        widget.bindtags((tag,)+tuple(t for t in widget.bindtags() if t!=tag));return
    widget.clipboard_keys_installed=True
    name=str(widget.cget('textvariable'))
    variable=tk.StringVar(master=widget,name=name) if name else tk.StringVar(master=widget,value=widget.get())
    if not name:widget.configure(textvariable=variable)
    widget._undo_var=variable;past=[];future=[];current=[variable.get()];replay=[False]
    def track(*args):
        new=variable.get()
        if not replay[0] and new!=current[0]:past.append(current[0]);del past[:-128];future.clear()
        current[0]=new
    trace=variable.trace_add('write',track)
    tag='ClipboardKeys'+str(widget)
    widget.bindtags((tag,)+widget.bindtags())
    def key(event):
        op=operation(event)
        if op in ('undo','redo'):
            if str(widget.cget('state')) in ('readonly','disabled'):return 'break'
            handler=getattr(widget,'field_command',None)
            if handler:handler(op);return 'break'
            src,dst=(past,future) if op=='undo' else (future,past)
            if src:
                dst.append(variable.get());replay[0]=True
                try:variable.set(src.pop());widget.icursor('end')
                finally:replay[0]=False
            return 'break'
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
            value=widget.get()
            a=int(widget.index('sel.first')) if widget.selection_present() else int(widget.index('insert'))
            b=int(widget.index('sel.last')) if widget.selection_present() else a
            variable.set(value[:a]+text+value[b:]);widget.icursor(a+len(text));widget.xview('insert')
        return 'break'
    widget.bind_class(tag,'<KeyPress>',key)
    from types import SimpleNamespace
    virtuals={'<<Copy>>':67,'<<Paste>>':86,'<<Cut>>':88,'<<SelectAll>>':65,'<<Undo>>':90,'<<Redo>>':89}
    for event,code in virtuals.items():widget.bind_class(tag,event,lambda e,c=code:key(SimpleNamespace(keycode=c,state=4)))
    def cleanup(event):
        if event.widget is widget:
            widget.unbind_class(tag,'<KeyPress>')
            for event in virtuals:widget.unbind_class(tag,event)
            variable.trace_remove('write',trace)
    widget.bind('<Destroy>',cleanup,add='+')
