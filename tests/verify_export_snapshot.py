"""Editable export and PDF must describe the same confirmed working snapshot."""
from pathlib import Path
import tempfile,queue
from openpyxl import Workbook,load_workbook
from openpyxl.workbook.defined_name import DefinedName
from pypdf import PdfReader
from workspace_preview import Session
from package_build import publish,Item

def wait(s,revision):
    while True:
        _,kind,data=s.events.get(timeout=60)
        if kind=='error':raise AssertionError(data)
        if kind=='pdf' and data[0]==revision:return data[1]

with tempfile.TemporaryDirectory() as td:
    p=Path(td);project=p/'Project';base=project/'Документы';base.mkdir(parents=True);(project/'project.json').write_text('{}')
    source=base/'Act.xlsx';w=Workbook();w.active['B2']='Original';w.defined_names.add(DefinedName('ID_User_test',attr_text="'Sheet'!$B$2"));w.save(source);w.close();original=source.read_bytes()
    s=Session(source,queue.Queue(),work_file=p/'working'/'Act.xlsx')
    try:
        wait(s,0);s.tasks.put(({'ID_User_test':'Changed'},1));pdf=wait(s,1)
        options=dict(version=True,combined=True,separate=False,individual=True,dedup=True,section_numbers=False,rebuild=False)
        out=publish(project,[Item(source,'КЖ','Акт',number='1')],p/'out',{source:pdf},options,lambda _:None,{source:(s.copy,s.clean_hash)})
        exported=load_workbook(p/'out'/'Project'/'Act.xlsx');assert exported.active['B2'].value=='Changed';exported.close()
        printed=next(out.rglob('*комплект.pdf'));assert 'Changed' in '\n'.join(page.extract_text() or '' for page in PdfReader(printed).pages)
        assert source.read_bytes()==original
        try:publish(project,[Item(source,'КЖ','Акт')],p/'wrong',{source:pdf},options,lambda _:None,{source:(s.copy,'0'*64)})
        except ValueError:pass
        else:raise AssertionError('mismatched document/PDF snapshot accepted')
    finally:s.tasks.put(None);s.thread.join(30)
    print('PASS exported editable data and printed PDF agree; untouched project source; revision/hash mismatch rejected')
