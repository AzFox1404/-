"""Resolve act fields against printed labels, including variants with inserted rows."""
from difflib import SequenceMatcher
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.utils.cell import coordinate_from_string
import re,json
from app_paths import ROOT,DATA_DIR,EXAMPLES_ROOT

def normalized(text):
    return ' '.join(str(text or '').lower().split())

def labels(sheet):
    return [(row[0].row,normalized(row[0].value)) for row in sheet.iter_rows(min_col=2,max_col=2)
            if row[0].value and isinstance(row[0].value,str)]

def reference_labels(typ,builtin_only=False):
    if not builtin_only:
        candidates=list((EXAMPLES_ROOT/'Шаблоны').glob('*'+typ+'*.xlsx'))
        if not candidates:candidates=list((DATA_DIR/'Библиотека'/'Шаблоны').rglob('Шаблон акта '+typ+'.xlsx'))
        if candidates:
            book=load_workbook(candidates[0],data_only=False)
            try:return labels(book.active)
            finally:book.close()
    return json.loads((ROOT/'data'/'act_anchors.json').read_text('utf-8')).get(typ,[])

def act_rows(file,*,builtin_only=False):
    if file.suffix.lower()!='.xlsx':return None
    wb=load_workbook(file,data_only=False);sheet=wb.active
    try:
        kind=next((normalized(r[0]) for r in sheet.iter_rows(min_col=2,max_col=2,max_row=40,values_only=True)
                   if re.match(r'^(?:акт\s+)?освидетельствования\s+(?:скрытых работ|ответственных конструкций)',normalized(r[0])) ), '')
        typ='АООК' if 'ответственных конструкций' in kind else 'АОСР' if 'скрытых работ' in kind else ''
        if not typ:return None
        a,b=reference_labels(typ,builtin_only),labels(sheet)
        if not a:return None
        chunks=SequenceMatcher(None,[v for _,v in a],[v for _,v in b],autojunk=False).get_matching_blocks()
        anchors={a[ix+k][0]:b[iy+k][0] for ix,iy,n in chunks for k in range(n)}
        def remap(coord,key,index):
            name=f'BID_field_{key}_{index}'
            if name in wb.defined_names:
                refs=list(wb.defined_names[name].destinations)
                if refs and refs[0][0]==sheet.title:return refs[0][1].replace('$','').split(':')[0]
            letter,row=coordinate_from_string(coord)
            # Locate inline values using the heading in the same row; for signatures
            # the following fine-print legend is a reliable anchor as well.
            if row in anchors:dest=anchors[row]
            else:
                following=[r for r in anchors if r>row]
                before=[r for r in anchors if r<row]
                if not following and not before:return None
                closest=min(before+following,key=lambda r:(abs(r-row),r<row))
                dest=anchors[closest]+row-closest
            if dest<1:return None
            cell=sheet[f'{letter}{dest}']
            value=str(cell.value or '').strip()
            if (letter=='B' and dest in anchors.values() and row not in anchors) or value.startswith('(') or (cell.font.sz is not None and cell.font.sz<=9 and value):
                return None
            if cell.__class__.__name__=='MergedCell':return None
            return cell.coordinate
        common={'address':['F2','B3' if typ=='АООК' else 'B4'],'client':['B6'],'clientAddress':['B8'],'builder':['B14'],'builderAddress':['B16'],'number':['B24'],'developer':['B28'],'builderRep':['B32'],'executorRep':['B35'],'executorInfo':['B37','B38'],'otherRep':['B41'],'executor':['F43']}
        if typ=='АОСР':
            extras=dict(work='H46',project='G48 B49',materials='F52',schemes='B55',start='F59',end='F60',date='L24',standards='B63 B64',nextWork='G67',notes='E69',attachments='C72',clientSign='F75',foreman='G77',executorSign='H79')
        else:
            extras=dict(work='H46 B47',project='G49 B50',materials='B54',hiddenWorks='B57',schemes='B62',reports='B65',tests='B68',start='F71',end='F72',date='L24',standards='B75 B76',nextWork='B85',notes='E88',attachments='C91',clientSign='F94',foreman='G96',executorSign='H98')
        common.update({k:v.split() for k,v in extras.items()})
        result={}
        for key,coords in common.items():
            resolved=[remap(c,key,i) for i,c in enumerate(coords)]
            valid=list(dict.fromkeys(c for c in resolved if c))
            if valid:result[key]=valid
        return {'kind':typ,'fields':result}
    
    finally:wb.close()
