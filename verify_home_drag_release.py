"""Regression: release must reach the controller when pointer is over its glass."""
import tempfile,time,tkinter as tk
from pathlib import Path
import studio

def pump(root,seconds=.08):
 end=time.monotonic()+seconds
 while time.monotonic()<end:root.update();time.sleep(.003)
with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
 root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]));pump(root,.3)
 split=app.home_layout[0];state=split.glass_state
 def descendants(w):
  for c in w.winfo_children():yield c;yield from descendants(c)
 from tkinter import ttk
 search=next(c for c in descendants(split) if isinstance(c,ttk.Entry))
 for offset in (40,-30,60,-20):
  search.focus_force();pump(root,.02)
  x,y=split.sash_coord(0);split.event_generate('<ButtonPress-1>',x=x+1,y=80);pump(root,.03)
  assert state['index']==0 and split.grab_current() is split
  cover=state['covers'][1]
  # Root coordinates reflect an event over the right-hand glass, not the sash.
  target=max(0,min(split.winfo_width()-1,x+offset))
  for sequence in ('<B1-Motion>','<ButtonRelease-1>'):
   cover.event_generate(sequence,x=target-cover.winfo_x(),y=80-cover.winfo_y(),rootx=split.winfo_rootx()+target,rooty=split.winfo_rooty()+80)
  pump(root)
  assert state['index'] is None and split.grab_current() is None
  assert not state['covers'] and not any(isinstance(c,tk.Canvas) for c in split.winfo_children())
 # The narrow line itself is also a child that can receive the physical release.
 x,y=split.sash_coord(0);split.event_generate('<ButtonPress-1>',x=x+1,y=80);pump(root,.02)
 state['line'].event_generate('<ButtonRelease-1>',x=1,y=70);pump(root)
 assert state['index'] is None and split.grab_current() is None
 # A quick mouse-up can still be addressed to the Entry beneath a not-yet-mapped cover.
 x,y=split.sash_coord(0);split.event_generate('<ButtonPress-1>',x=x+1,y=80)
 search.event_generate('<ButtonRelease-1>',x=5,y=5);pump(root)
 assert state['index'] is None and split.grab_current() is None
 assert not any('GlassDrag' in tag for tag in search.bindtags())
 # Escape, focus loss and interrupted/unmapped windows release the mouse as well.
 for event in ('<Escape>','<FocusOut>','<Unmap>'):
  x,y=split.sash_coord(0);split.event_generate('<ButtonPress-1>',x=x+1,y=80);pump(root,.02)
  assert state['index'] is not None
  if event=='<Escape>':split.focus_force()
  split.event_generate(event);pump(root)
  assert state['index'] is None and split.grab_current() is None,event
 assert not errors,errors
 # Still responds to ordinary actions after all the drags.
 dark=app.dark;app.toggle_theme(not dark);pump(root);assert app.dark!=dark
 app.close();print('PASS actual home screen: release over both glass/line, repeated drags, Escape/focus loss/unmap; no retained grab or overlays; theme still responds',flush=True)
