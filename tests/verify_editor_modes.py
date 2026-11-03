"""Empty date placeholders and fullscreen from a hidden landing page."""
import tkinter as tk,tempfile,time
from pathlib import Path
import studio
from workspace_preview import Workspace
from pdf_page_preview import PagePreview

def pump(root):
 end=time.monotonic()+.15
 while time.monotonic()<end:root.update();time.sleep(.005)
with tempfile.TemporaryDirectory() as td:
 p=Path(td);studio.STORE=p;studio.PROJECTS=p/'projects';studio.LIB=p/'library';studio.SAMPLES=p/'missing/sample'
 root=tk.Tk();app=studio.Studio(root);errors=[];root.report_callback_exception=lambda *e:errors.append(str(e[1]));pump(root)
 app.landing.pack_forget();editor=tk.Frame(root);editor.pack(fill='both',expand=True)
 root.state('zoomed');pump(root)
 button=app.full_buttons[0]
 # Same callback as the visible editor's fullscreen icon.
 app.toggle_fullscreen();pump(root);assert root.attributes('-fullscreen')
 app.toggle_fullscreen();pump(root);assert not root.attributes('-fullscreen') and root.state()=='zoomed'
 root.app_caption.buttons[1].invoke();pump(root);assert root.state()=='normal' and not root.attributes('-fullscreen')
 win=tk.Toplevel(root);view=PagePreview(win,app);view.pack(fill='both',expand=True);win.geometry('600x500');pump(root)
 view.show_draft('test','Short text','Field');pump(root)
 assert view.draft_area.winfo_height()<85,view.draft_area.winfo_height()
 view.show_draft('test','Long text '*400,'Field');pump(root);assert view.draft_area.winfo_height()<230
 for value in ('','"  "    202 г.','__.__.202_','not a date'):
  assert Workspace.human(value)==''
 assert Workspace.human('2026-11-03')=='03.11.2026'
 root.destroy();assert not errors,errors
print('PASS editor fullscreen from maximized window, title restore, empty dates and compact draft')
