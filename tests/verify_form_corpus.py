"""Optional private-corpus verification. All Office edits use isolated copies.

Set BUREAU_FORM_CORPUS and BUREAU_FORM_REPORT to explicit local directories.
The report and generated documents must remain outside source control.
"""
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import tempfile

import pymupdf
from workspace_preview import Session


def wait_for(session, kind):
    while True:
        try:
            _, event, payload = session.events.get(timeout=180)
        except queue.Empty:
            raise TimeoutError('Office did not return a result within 180 seconds')
        if event == 'error':
            raise RuntimeError(payload)
        if event == kind:
            return payload


def check_document(source, directory, modes=('long', 'clear', 'refill')):
    work = directory/source.name
    shutil.copy2(source, work)
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    session = Session(work, queue.Queue(), prepared=True)
    result = dict(steps=[])
    try:
        values = wait_for(session, 'fields')
        wait_for(session, 'pdf')
        result['fields'] = len(values)
        keys = [key for key in values
                if session.spec.get(key, {}).get('kind', 'text') == 'text'
                and key not in ('start', 'end', 'date')]
        tokens = {key: f'CHECK{index:04d}' for index, key in enumerate(keys)}
        for revision, mode in enumerate(modes, 1):
            for key, token in tokens.items():
                values[key] = '' if mode == 'clear' else (
                    ('Контроль '+token+' ')*4 if mode == 'long' else 'Контроль '+token)
            if 'copies' in values:values['copies']='' if mode=='clear' else '12' if mode=='long' else '3'
            session.tasks.put((dict(values), revision))
            wait_for(session, 'pdf')
            pdf = directory/(mode+'.pdf')
            shutil.copy2(session.preview_dir/'Предпросмотр.pdf', pdf)
            with pymupdf.open(pdf) as document:
                printed = ''.join(''.join(page.get_text().split()) for page in document)
                missing = [key for key, token in tokens.items()
                           if printed.count(token) != (0 if mode=='clear' else 4 if mode=='long' else 1)]
                if 'copies' in values and not re.search('актсоставленв'+values['copies']+r'(?:-[хти]+)?экземпляр',printed,re.I):missing.append('copies')
                result['steps'].append(dict(mode=mode, pages=len(document), missing=missing))
            if session.formula_errors:
                raise AssertionError(session.formula_errors)
    except Exception as error:
        result['error'] = repr(error)
    finally:
        session.tasks.put(None)
        session.thread.join(35)
        if session.thread.is_alive():
            raise RuntimeError('Office session did not stop; corpus run aborted')
        result['source_unchanged'] = hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    return result


if __name__ == '__main__':
    source_root = Path(os.environ['BUREAU_FORM_CORPUS']).resolve()
    report_root = Path(os.environ['BUREAU_FORM_REPORT']).resolve()
    report_root.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix='bureau-form-corpus-') as temp:
        for index, source in enumerate(sorted(source_root.rglob('*'))):
            if not source.is_file() or source.suffix.lower() not in ('.doc', '.docx', '.xlsx'):
                continue
            directory = Path(temp)/str(index)
            directory.mkdir()
            result = check_document(source, directory)
            result['file'] = str(source.relative_to(source_root))
            results.append(result)
            output = report_root/str(index)
            output.mkdir(exist_ok=True)
            for pdf in directory.glob('*.pdf'):
                shutil.copy2(pdf, output/pdf.name)
            (report_root/'report.json').write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
            print(len(results), result['file'], result.get('error', 'completed'), flush=True)
    failures = [result for result in results if result.get('error') or not result['source_unchanged']
                or result['fields'] == 0
                or any(step['missing'] for step in result['steps'])]
    assert not failures, f'{len(failures)} documents require review; see report.json'
