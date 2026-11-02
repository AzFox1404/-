"""Browser-like middle-button autoscroll, with distance and hold acceleration."""
import time,math,tkinter as tk
from tkinter import ttk

def install(widget):
 if getattr(widget,'_auto_scroll',False):return
 widget._auto_scroll=True;state={'active':False,'timer':None,'origin':None,'started':0,'rx':0.,'ry':0.,'cursor':None};widget.auto_scroll_state=state
 def stop(event=None):
  state['active']=False
  if state['timer'] is not None:
   try:widget.after_cancel(state['timer'])
   except tk.TclError:pass
   state['timer']=None
  if widget.winfo_exists():
   if state['cursor'] is not None:widget.configure(cursor=state['cursor'])
   if isinstance(widget,tk.Canvas):widget.delete('auto-scroll-origin')
 def move(axis,pixels):
  if not pixels:return
  if isinstance(widget,tk.Canvas):
   region=widget.tk.splitlist(widget.cget('scrollregion'))
   if len(region)!=4:return
   extent=float(region[2 if axis=='x' else 3])-float(region[0 if axis=='x' else 1])
   if extent>0:getattr(widget,axis+'view_moveto')(getattr(widget,axis+'view')()[0]+pixels/extent)
  else:
   key='rx' if axis=='x' else 'ry';state[key]+=pixels/(12 if axis=='x' else 22)
   units=math.trunc(state[key]);state[key]-=units
   if units:getattr(widget,axis+'view_scroll')(units,'units')
 def tick():
  state['timer']=None
  if not state['active'] or not widget.winfo_exists():return
  x,y=widget.winfo_pointerxy();ox,oy=state['origin'];factor=1+min(2,(time.monotonic()-state['started'])/5)
  def velocity(distance):
   d=max(0,abs(distance)-10);return math.copysign(min(4000,d**1.5*.7*factor)*.02,distance)
  move('x',velocity(x-ox));move('y',velocity(y-oy));state['timer']=widget.after(20,tick)
 def toggle(event):
  if state['active']:stop();return 'break'
  state.update(active=True,origin=(event.x_root,event.y_root),started=time.monotonic(),rx=0.,ry=0.,cursor=widget.cget('cursor'))
  widget.focus_set();widget.configure(cursor='fleur')
  if isinstance(widget,tk.Canvas):
   x,y=widget.canvasx(event.x),widget.canvasy(event.y)
   widget.create_oval(x-10,y-10,x+10,y+10,fill='#eee6df',outline='#756a63',tags='auto-scroll-origin')
   widget.create_text(x,y,text='↕',fill='#312b29',tags='auto-scroll-origin')
  state['timer']=widget.after(20,tick);return 'break'
 widget.bind('<Button-2>',toggle,add='+')
 for event in ('<Escape>','<Button-1>','<Button-3>','<MouseWheel>','<FocusOut>','<Unmap>','<Destroy>'):widget.bind(event,stop,add='+')
 widget.stop_auto_scroll=stop
 widget.toggle_auto_scroll=toggle
 def cancel_first(event):
  target=event.widget;active=getattr(target,'auto_scroll_state',{}).get('active',False)
  if active:target.stop_auto_scroll()
  if active and event.keysym=='Escape':return 'break'
 widget.bindtags(('AutoScrollCancel',)+tuple(t for t in widget.bindtags() if t!='AutoScrollCancel'))
 root=widget._root()
 if not getattr(root,'_auto_cancel_installed',False):
  root._auto_cancel_installed=True
  for event in ('<Escape>','<Button-1>','<Button-3>','<MouseWheel>'):
   root.bind_class('AutoScrollCancel',event,cancel_first)
