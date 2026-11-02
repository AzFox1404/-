"""Windows Explorer OLE drop target provided by the bundled TkDND extension."""
from pathlib import Path

def accept_files(widget, handler):
    tk=widget.tk
    lib=Path(__file__).resolve().parents[1]/'vendor'/'tkdnd-win-x64'
    if not tk.call('package','provide','tkdnd'):
        tk.call('lappend','auto_path',str(lib))
        tk.call('package','require','tkdnd')
    tk.call('tkdnd::drop_target','register',str(widget),'DND_Files')
    def dropped(data):
        paths=[Path(item) for item in tk.splitlist(data)]
        widget.after_idle(lambda:handler(paths))
        return 'copy'
    command=widget.register(dropped)
    tk.call('bind',str(widget),'<<Drop:DND_Files>>',command+' %D')
    tk.call('bind',str(widget),'<<Drop>>',command+' %D')
