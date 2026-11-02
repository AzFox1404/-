"""A rejected save must leave the editable session alive for correction/discard."""
import tempfile,threading,queue,tkinter as tk
from pathlib import Path
from types import SimpleNamespace
import studio,save_decisions

with tempfile.TemporaryDirectory() as td:
    p=Path(td);studio.STORE=p/'store';studio.PROJECTS=studio.STORE/'Проекты';studio.LIB=studio.STORE/'Библиотека/Шаблоны'
    project=p/'project';(project/'Документы').mkdir(parents=True);(project/'project.json').write_text('{}')
    source=project/'Документы'/'Bad.xlsx';source.write_bytes(b'original')
    root=tk.Tk();app=studio.Studio(root);app.project=project
    class Session:pass
    s=Session();s.source=source;s.tasks=queue.Queue();s.row_operation_busy=False;s.row_operations=[];s.validated_revision=1;s.formula_errors=['Sheet!A1']
    event=threading.Event();s.thread=threading.Thread(target=event.wait);s.thread.start()
    app.sessions={source:s};app.pending={};app.revisions={s:1};app.saved_rev={s:1};app.models={s:{}};app.latest={}
    errors=[];save_decisions.messagebox.showerror=lambda *a,**k:errors.append(a)
    completed=[];app.stop_sessions([s],lambda:completed.append(True),require_saved=True);root.update()
    assert errors and not completed and s.thread.is_alive() and s.tasks.empty() and app.sessions[source] is s
    assert source.read_bytes()==b'original' and not app.stopping
    event.set();s.thread.join();root.destroy()
    print('PASS formula rejection preserves source, worker, session and ability to correct/discard')
