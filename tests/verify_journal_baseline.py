"""Immutable opening baseline survives explicit document saves and recovery."""
from pathlib import Path
import tempfile
from save_decisions import ProjectJournal

with tempfile.TemporaryDirectory() as td:
    project=Path(td);base=project/'Документы';base.mkdir()
    file=base/'A.docx';file.write_bytes(b'original');(project/'project.json').write_bytes(b'{}')
    j=ProjectJournal(project);j.protect(file)
    new=base/'Folder'/'New.docx';new.parent.mkdir();file.rename(new);j.removed.add(file);j.move_paths(file,new)
    j.work_file(new).parent.mkdir(parents=True,exist_ok=True);j.work_file(new).write_bytes(b'explicit save')
    assert new.read_bytes()==b'original'
    j.dirty.add(new);j.publish_working(new);j.commit_document(new)
    renamed=new.with_name('Temporary.docx');new.rename(renamed);j.move_paths(new,renamed)
    j.dirty.add(renamed)
    assert j.restore_document(renamed)==new and not renamed.exists()
    j.dirty.add(new);new.write_bytes(b'legacy mutation');j.restore_document(new)
    assert new.read_bytes()==b'explicit save' and j.dirty_project()
    recovered=ProjectJournal(project)
    assert recovered.origins[new.relative_to(base)]==Path('A.docx')
    recovered.restore()
    assert file.read_bytes()==b'original' and not new.exists() and not new.parent.exists()
    assert (project/'project.json').read_bytes()==b'{}'
    recovered.temp.cleanup()
    print('PASS document checkpoint, renamed paths, persisted recovery and exact opening-state project restore')
