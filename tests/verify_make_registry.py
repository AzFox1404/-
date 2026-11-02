from pathlib import Path
import tempfile
from openpyxl import load_workbook
from pypdf import PdfReader
from app_paths import EXAMPLES_ROOT
from package_build import make_registry

source=EXAMPLES_ROOT/'Реестр.xlsx';before=source.read_bytes()
with tempfile.TemporaryDirectory() as td:
    p=Path(td);out=p/'Реестр.xlsx';pdf=p/'Реестр.pdf'
    rows=[dict(title='АОСР Test A',number='КЖ-1',date='01.11.2026',count=3,span='1-3'),dict(title='АОСР Test B',number='КЖ-2',date='02.11.2026',count=2,span='4-5')]
    make_registry(source,out,pdf,rows)
    book=load_workbook(out,data_only=True);ws=book.active
    assert [ws[f'A{r}'].value for r in (8,9)]==[1,2]
    assert [ws[f'E{r}'].value for r in (8,9)]==[3,2]
    assert [ws[f'F{r}'].value for r in (8,9)]==['1-3','4-5']
    assert not any(cell.data_type=='e' for row in ws for cell in row)
    assert not any('Всего позиций' in str(c.value) for row in ws for c in row)
    book.close();formulas=load_workbook(out);assert formulas.active['A8'].data_type=='f';formulas.close()
    assert len(PdfReader(pdf).pages)==1 and source.read_bytes()==before
    print('PASS rebuilt registry ordinals/formulas, leaf counts and page ranges; no summary in general register; one-page PDF; original unchanged')
