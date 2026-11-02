"""Accelerated horizontal selection when dragging past the edge of a text field."""
import time
from tkinter import ttk

def install(widget):
    if getattr(widget,'drag_scroll_installed',False):return
    widget.drag_scroll_installed=True
    state={'pressed':False,'anchor':0,'x':0,'since':0,'timer':None}
    def cancel(*args):
        state['pressed']=False
        if state['timer'] is not None:
            try:widget.after_cancel(state['timer'])
            except Exception:pass
            state['timer']=None
    def tick():
        state['timer']=None
        if not state['pressed'] or not widget.winfo_exists():return
        width=widget.winfo_width()
        direction=-1 if state['x']<0 else 1 if state['x']>width else 0
        if not direction:return
        elapsed=max(0,time.monotonic()-state['since'])
        step=min(50,1+int(elapsed*elapsed*3)+int(max(0,abs(state['x']-width/2)-width/2)/12))
        current=int(widget.index('insert'));end=int(widget.index('end'))
        pos=max(0,min(end,current+direction*step))
        widget.icursor(pos);widget.selection_range(min(state['anchor'],pos),max(state['anchor'],pos))
        widget.xview_scroll(direction*step,'units')
        state['timer']=widget.after(45,tick)
    def press(event):
        if isinstance(widget,ttk.Combobox) and event.x>widget.winfo_width()-22:return
        cancel();state.update(pressed=True,anchor=int(widget.index('@'+str(event.x))),x=event.x,since=time.monotonic())
    def motion(event):
        if not state['pressed']:return
        state['x']=event.x
        if event.x<0 or event.x>widget.winfo_width():
            if state['timer'] is None:tick()
            return 'break'
        state['since']=time.monotonic()
        if state['timer'] is not None:widget.after_cancel(state['timer']);state['timer']=None
    widget.bind('<ButtonPress-1>',press,add='+');widget.bind('<B1-Motion>',motion)
    for event in ('<ButtonRelease-1>','<Destroy>','<Unmap>'):widget.bind(event,cancel,add='+')
