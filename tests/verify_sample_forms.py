"""Exemplar transfers are explicit, structural and never touch private samples."""
import tempfile,hashlib
from pathlib import Path
from docx import Document
from openpyxl import Workbook
import sample_forms as sf
from word_fields import bookmark,analyze_word,text

with tempfile.TemporaryDirectory() as td:
    root=Path(td);sf.FILE=root/'profiles.json'
    d=Document();d.add_paragraph('Форма проверки');d.add_paragraph('Заказчик')
    p=d.add_paragraph();run=p.add_run('Компания Альфа');run.bold=True;run.italic=True;run.underline=True
    d.add_paragraph('(наименование организации)')
    bookmark(p._p,0,len(p.text),'Confirmed_1',100)
    prepared=root/'confirmed.docx';d.save(prepared)
    fields={'confirmedClient':dict(label='Заказчик',segments=[dict(bookmark='Confirmed_1')])}
    profile=sf.word_profile(prepared,fields);sf.remember(profile)
    # Repeated training is idempotent.
    sf.remember(profile);assert len(sf.read(sf.FILE)['profiles'])==1
    for replacement in ('Компания Бета',''):
        n=Document(prepared);n.paragraphs[2].runs[0].text=replacement
        source=root/'new.docx';n.save(source);original=source.read_bytes()
        plan=analyze_word(source,root/'out.docx')
        assert plan['kind']=='custom' and plan['fields']['confirmedClient']['value']==replacement
        assert source.read_bytes()==original
        out=Document(root/'out.docx');assert out.paragraphs[2].runs[0].bold and out.paragraphs[2].runs[0].underline
        assert out.paragraphs[3].text=='(наименование организации)'
    n=Document(prepared);n.paragraphs[1].text='Подпись ответственного лица';bad=root/'bad.docx';n.save(bad)
    assert not analyze_word(bad)['fields'],'changed permanent caption must invalidate transfer'
    w=Workbook();s=w.active;s['A1']='Реестр образца';s['A2']='Наименование';s['B2']='Компания Альфа';s['A3']='Дата';s['B3']='01.01.2026';s.merge_cells('A5:B5');s['A5']='(пояснение)'
    excel=sf.excel_profile(s,{'company':dict(dest='B2',label='Организация')});sf.remember(excel)
    s['B2']='Компания Бета';result=sf.apply_excel(s,{})
    assert result['company']['value']=='Компания Бета' and result['company']['dest']=='B2'
    existing={'known':dict(dest='B2',value='Known')};assert sf.apply_excel(s,existing)==existing
    s['B2']='=1+2';assert not sf.apply_excel(s,{})
    s['B2']='Компания';s['A2']='Подпись';assert not sf.apply_excel(s,{})
    personal={'keys':{'client':['Личный заказчик']},'labels':{}}
    assert sf.personal_choices('titleClient','',personal)==['Личный заказчик']
    # Order fields preserve static commands and only expose the value spans.
    order=Document();order.add_paragraph('Приказ № 15-П');order.add_paragraph('01.01.2026 г.');order.add_paragraph('ПРИКАЗЫВАЮ:');order.add_paragraph('Назначить Иванова Ивана Ивановича, производителя работ ответственным.')
    source=root/'order.docx';order.save(source);plan=analyze_word(source)
    assert plan['kind']=='order' and plan['fields']['orderNumber']['value']=='15-П'
    assert plan['fields']['orderAppointee']['value']=='Иванова Ивана Ивановича'
    assert all(f['value']!='ПРИКАЗЫВАЮ:' for f in plan['fields'].values())
print('PASS confirmed Word/Excel structural transfer, blank slot, unchanged source/styles/captions, guard rejection, formula protection, existing precedence, idempotent learning, personal aliases and orders')
