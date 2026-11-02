"""Passive rounded tooltips, including inactive windows under the mouse."""
import tkinter as tk
from tkinter import ttk
import ctypes as C
import os

def active_application():
 u=C.windll.user32;u.GetForegroundWindow.restype=C.c_void_p;pid=C.c_uint();u.GetWindowThreadProcessId(C.c_void_p(u.GetForegroundWindow()),C.byref(pid));return pid.value==os.getpid()

def tooltip(widget,message):
 # Visible action labels already explain full-size buttons. Keep hints for
 # icon-only controls and option checkboxes, whose effects need explanation.
 if isinstance(widget,(ttk.Button,tk.Button,ttk.Menubutton)) and str(widget.cget('text')).strip() not in ('','—','□','↗'):
  return
 if getattr(widget,'has_hint',False):return
 widget.has_hint=True;widget.hint_message=message;state={'timer':None,'window':None,'monitor':None};widget.hint_state=state
 def hide(*args):
  if state.get('monitor') is not None:
   try:widget.after_cancel(state['monitor'])
   except tk.TclError:pass
   state['monitor']=None
  if state['timer'] is not None:
   try:widget.after_cancel(state['timer'])
   except tk.TclError:pass
   state['timer']=None
  if state['window'] is not None:
   try:state['window'].destroy()
   except tk.TclError:pass
   state['window']=None
 def show():
  state['timer']=None
  if not widget.winfo_exists() or not widget.winfo_viewable():return
  from PIL import ImageColor
  bg=ttk.Style(widget).lookup('TFrame','background') or '#faf5f1'
  try:dark=sum(ImageColor.getrgb(bg))<384
  except ValueError:dark=False
  fill='#d3d1d0' if dark else '#ffffff'
  win=tk.Toplevel(widget);win.overrideredirect(True);win.transient(widget.winfo_toplevel());win.attributes('-topmost',True);state['window']=win
  canvas=tk.Canvas(win,highlightthickness=0,bg=fill)
  text=message() if callable(message) else message
  item=canvas.create_text(10,8,text=text,fill='#111111',width=330,anchor='nw',font=('Segoe UI',9))
  box=canvas.bbox(item);w=box[2]+10;h=box[3]+8;canvas.configure(width=w,height=h);canvas.pack()
  from PIL import Image,ImageDraw,ImageTk
  border=Image.new('RGB',(w*4,h*4),fill);ImageDraw.Draw(border).rounded_rectangle((2,2,w*4-3,h*4-3),radius=20,fill=fill,outline='#a9a5a2',width=4)
  canvas.border_image=ImageTk.PhotoImage(border.resize((w,h),Image.Resampling.LANCZOS),master=canvas)
  canvas.create_image(0,0,image=canvas.border_image,anchor='nw');canvas.tag_raise(item)
  x=widget.winfo_rootx();y=widget.winfo_rooty()+widget.winfo_height()+5
  x=max(0,min(x,widget.winfo_screenwidth()-w-6))
  if y+h>widget.winfo_screenheight():y=widget.winfo_rooty()-h-5
  win.geometry(f'{w}x{h}+{x}+{y}');win.update_idletasks()
  try:
   u=C.windll.user32;u.GetParent.argtypes=[C.c_void_p];u.GetParent.restype=C.c_void_p
   hwnd=u.GetParent(win.winfo_id()) or win.winfo_id()
   g=C.windll.gdi32;g.CreateRoundRectRgn.restype=C.c_void_p
   region=g.CreateRoundRectRgn(0,0,w+1,h+1,10,10)
   u.SetWindowRgn.argtypes=[C.c_void_p,C.c_void_p,C.c_bool];u.SetWindowRgn(hwnd,region,True)
  except (AttributeError,OSError):pass
  win.lift()
  foreground=C.windll.user32.GetForegroundWindow()
  def monitor():
   state['monitor']=None
   if state['window'] is not win:return
   if not active_application() and C.windll.user32.GetForegroundWindow()!=foreground:hide();return
   state['monitor']=widget.after(100,monitor)
  state['monitor']=widget.after(100,monitor)
 widget.show_hint=show
 def enter(e):hide();state['timer']=widget.after(400,show)
 widget.bind('<Enter>',enter,add='+')
 for event in ('<Leave>','<ButtonPress>','<Unmap>','<Destroy>'):widget.bind(event,hide,add='+')
def hover_icon(widget,app,key):
 """Keep ttk action glyphs legible on the shared pale hover surface."""
 from command_icons import command_icon
 widget.icon_name=key
 def enter(event):
  widget.hover_image=command_icon(widget,key,'#111111');widget.configure(image=widget.hover_image)
 def leave(event):
  if widget.winfo_exists():widget.configure(image=app.icon(key))
 widget.bind('<Enter>',enter,add='+');widget.bind('<Leave>',leave,add='+')
