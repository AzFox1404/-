"""Office cache proof, formula results/errors, and environment/content invalidation."""
import tempfile,queue,os,json
from pathlib import Path
from openpyxl import Workbook,load_workbook
from workspace_preview import Session
from final_pdf_cache import FinalPDFCache,digest,environment

def exported(session):
    while True:
        _,kind,data=session.events.get(timeout=60)
        if kind=='error':raise AssertionError(data)
        if kind=='pdf':return data[1]

with tempfile.TemporaryDirectory() as td:
    p=Path(td);cache=FinalPDFCache(p/'cache')
    for broken in (False,True):
        source=p/('bad.xlsx' if broken else 'good.xlsx');w=Workbook();w.active['A1']='=1/0' if broken else '=1+2';w.active['B2']='=SUM(A1,4)';w.active.merge_cells('C4:D4');w.active['C4']='Fixed caption';w.save(source);w.close()
        initial=source.read_bytes();s=Session(source,queue.Queue(),work_file=p/'work'/source.name)
        try:
            pdf=exported(s);assert source.read_bytes()==initial
            assert bool(s.formula_errors)==broken,s.formula_errors
            if broken:
                assert not cache.put(s.copy,pdf,s.clean_hash,s.formula_errors)
                continue
            saved=load_workbook(s.copy,data_only=True);assert saved.active['A1'].value==3 and saved.active['B2'].value==7;saved.close()
            saved=load_workbook(s.copy);assert saved.active['A1'].value=='=1+2' and str(next(iter(saved.active.merged_cells.ranges)))=='C4:D4';saved.close()
            assert cache.put(s.copy,pdf,s.clean_hash) and cache.get(s.copy)==pdf
            meta=next((p/'cache').glob('*.json'));m=json.loads(meta.read_text());assert m['source_sha256']==digest(s.copy)
            old_profile=os.environ.get('BUREAU_ID_PDF_PROFILE');os.environ['BUREAU_ID_PDF_PROFILE']='different-printer-or-policy';environment.cache_clear()
            assert cache.get(s.copy) is None
            if old_profile is None:os.environ.pop('BUREAU_ID_PDF_PROFILE')
            else:os.environ['BUREAU_ID_PDF_PROFILE']=old_profile
            environment.cache_clear();assert cache.get(s.copy)==pdf
            (p/'cache'/(m['key']+'.pdf')).write_bytes(b'corrupt');assert cache.get(s.copy) is None
            import shutil
            mutated=p/'mutated'/s.copy.name;mutated.parent.mkdir();shutil.copy2(s.copy,mutated)
            with mutated.open('ab') as f:f.write(b'changed')
            assert cache.get(mutated) is None
            print('TIMING',s.timings[-1])
        finally:s.tasks.put(None);s.thread.join(30)
    print('PASS exact source preservation; formulas 3/7, merged range; formula errors blocked from final cache; PDF checksum, environment and content invalidation')
