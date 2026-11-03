"""Word notes caption survives real Office writes; original stays immutable."""
import tempfile,queue
from pathlib import Path
from docx import Document
from workspace_preview import Session

def wait(s,kind):
    while True:
        _,event,data=s.events.get(timeout=60)
        if event=='error':raise AssertionError(data)
        if event==kind:return data

with tempfile.TemporaryDirectory() as td:
    p=Path(td);source=p/'act.docx';doc=Document()
    doc.add_paragraph('АКТ освидетельствования скрытых работ')
    title=doc.add_paragraph('Дополнительные сведения:');title.runs[0].bold=True
    doc.add_paragraph().add_run('').underline=True
    doc.add_paragraph('Акт составлен в 3 экземплярах');doc.save(source);before=source.read_bytes()
    s=Session(source,queue.Queue(),work_file=p/'working.docx')
    try:
        values=wait(s,'fields');wait(s,'pdf');assert values['notes']==''
        for revision,value in enumerate(('Дополнение',''),1):
            values['notes']=value;s.tasks.put((dict(values),revision));wait(s,'pdf')
            result=Document(s.copy)
            assert result.paragraphs[1].text=='Дополнительные сведения:'
            assert result.paragraphs[1].runs[0].bold
            assert result.paragraphs[2].text==value
            assert source.read_bytes()==before
    finally:s.tasks.put(None);s.thread.join(30)
print('PASS Office notes fill/clear keeps bold caption and colon, separate editable line and immutable source')
