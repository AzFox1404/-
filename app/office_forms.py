"""Explicit value locations for the title, inventory and its two attachment layouts."""
import datetime
import re
from pathlib import Path

def instruction(value):
    value=str(value or '').strip()
    return value.startswith('(') or bool(re.match(r'^(?:ИНН, адреса юридического лица|адрес юридического лица в пределах его места|является указанное юридическое лицо)',value,re.I))

def _existing_fields(path):
    fields={}
    def add(k,dest,value,label,kind='text',prefix=''):
        if instruction(value):return
        if any(f['dest']==dest for f in fields.values()):return
        fields[k]=dict(dest=dest,value=str(value or ''),label=label,kind=kind,prefix=prefix)
    if path.suffix.lower()=='.docx':
        from docx import Document
        paras=Document(path).paragraphs
        if not any('ИСПОЛНИТЕЛЬНАЯ ДОКУМЕНТАЦИЯ' in p.text for p in paras):return {}
        count=0;sections=0
        for i,p in enumerate(paras):
            txt=p.text
            match=re.match(r'^(\s*(?:ЗАКАЗЧИК:|Объект:|шифр проекта)\s*)(.*)$',txt,re.I)
            if match:
                prefix,val=match.groups()
                if 'шифр' in prefix.lower():count+=1;k=f'code{count}';label=f'Шифр проекта {count}'
                elif 'заказчик' in prefix.lower():k,label='titleClient','Заказчик'
                else:k,label='titleAddress','Объект и адрес'
                add(k,i+1,val,label,prefix=prefix)
            elif txt.strip()=='Раздел' and i+1<len(paras):
                sections+=1;add(f'section{sections}',i+2,paras[i+1].text,f'Раздел {sections}')
            elif re.match(r'^г\.\s',txt):add('cityYear',i+1,txt,'Город и год')
        return fields
    if path.suffix.lower()!='.xlsx':return {}
    from openpyxl import load_workbook
    w=load_workbook(path,read_only=False,data_only=False)
    try:rows=list(w.active.values)
    finally:w.close()
    def cell(row,col):return rows[row-1][col-1] if row<=len(rows) and col<=len(rows[row-1]) else None
    general='РЕЕСТР ИСПОЛНИТЕЛЬНОЙ' in str(cell(5,1)).upper()
    quality='материал' in str(cell(8,2)).lower()
    schemes='Наименование документа' in str(cell(8,2)) and 'Номер документа' in str(cell(8,3))
    if not (general or quality or schemes):
        from register_layout import register_fields
        return register_fields(path)
    cached=None
    def xl(row,col,key,label,kind='text',prefix=''):
        nonlocal cached
        if label=='Страницы':return  # Derived from the sheet counts, never user input.
        addr=chr(64+col)+str(row);v=cell(row,col)
        if isinstance(v,str) and v.startswith('='):
            if label not in ('Страницы','Количество листов'):return
            if cached is None:
                ref=load_workbook(path,read_only=True,data_only=True)
                try:cached=list(ref.active.values)
                finally:ref.close()
            v=cached[row-1][col-1]
        if prefix and isinstance(v,str) and v.startswith(prefix.rstrip()):v=v[len(prefix.rstrip()):].lstrip()
        if isinstance(v,(datetime.datetime,datetime.date)):v=v.strftime('%d.%m.%Y')
        add(key,addr,v,label,kind,prefix)
    if general:
        xl(1,1,'regFirm','Организация и реквизиты');xl(3,2,'regAddress','Объект и адрес')
    else:
        col=3 if quality else 2
        xl(2,col,'actRef','Акт, номер и дата');xl(4,1,'regAddress','Объект и адрес',prefix='Объект: ')
        xl(6,3 if quality else 1,'regTitle','Наименование и номер приложения')
    table_end=next((r for r in range(9,len(rows)+1) if any('Всего страниц' in str(v) for v in rows[r-1]) or cell(r,1) in ('Передал','Принял')),len(rows)+1)
    totals=None
    for r in range(8 if general else 9,len(rows)+1):
        first=cell(r,1)
        if any('Всего страниц' in str(v) for v in rows[r-1]):totals=r;continue
        if general and not cell(r,2) and not instruction(first) and (r==8 or isinstance(first,str) and not first.startswith('=') and first not in ('Передал','Принял')):
            subgroup=bool(re.match(r'^(АОСР|АООК|Акты|Исполнительные схемы|Паспорта|Сертификаты|Приложения)',str(first or ''),re.I))
            xl(r,1,('group' if subgroup else 'part')+str(r),('Группа документов' if subgroup else 'Раздел комплекта')+' · строка '+str(r))
        if general and first in ('Передал','Принял'):
            xl(r,2,f'sign{r}',first+' · подпись');xl(r,4,f'signDate{r}',first+' · дата')
        blank_position=not str(first or '').strip() and r<table_end and w.active.cell(r,2).__class__.__name__!='MergedCell' and bool(w.active.cell(r,2).border.bottom.style)
        if not (isinstance(first,(float,int)) or str(first).startswith('=') or blank_position):continue
        labels=(['Наименование документа','Номер','Дата','Количество листов','Страницы'] if general else
                ['Материал','Вид документа','Номер документа','Дата','Количество листов'] if quality else
                ['Наименование документа','Номер документа','Дата','Количество листов'])
        for c,label in enumerate(labels,2):
            xl(r,c,f'row{r}_{c}',label,'datecell' if label=='Дата' else 'number' if label=='Количество листов' else 'text')
    if totals:
        for r in range(totals+1,len(rows)+1):
            if instruction(cell(r,2)):
                for c in (2,4,5):
                    if cell(r-1,c):xl(r-1,c,f'sig{r}_{c}','Подписание · '+str(cell(r-1,c)))
                if r>2:
                    for c in (4,5):
                        if cell(r-2,c):xl(r-2,c,f'initials{r}_{c}','Подписание · фамилия и инициалы')
                if r>2 and cell(r-2,2)=='Производитель работ':
                    xl(r-2,2,f'role{r}','Должность');xl(r-2,5,f'person{r}','Фамилия и инициалы')
    from register_layout import register_fields
    destinations={field['dest'] for field in fields.values()}
    for key,field in register_fields(path).items():
        if key not in fields and field['dest'] not in destinations:
            fields[key]=field
            destinations.add(field['dest'])
    return fields



def extra_fields(path):
    fields=_existing_fields(path)
    if path.suffix.lower()=='.xlsx':
        from manual_excel import fields as supplement
        fields=supplement(path,fields)
        from openpyxl import load_workbook
        book=load_workbook(path,data_only=False)
        try:
            for row in book.active:
                for cell in row:
                    if not isinstance(cell.value,str) or cell.data_type=='f':continue
                    match=re.search(r'(Акт составлен в[ \t\u00a0]*?)(\d+|[ _\t\u00a0]+)((?:-[хти]+)?[ \t\u00a0]*экземпляр.*)',cell.value,re.I)
                    if match:
                        prefix=cell.value[:match.start(2)];suffix=cell.value[match.end(2):]
                        if not prefix.endswith((' ','\t','\u00a0')):prefix+=' '
                        if not suffix.startswith((' ','\t','\u00a0','-')):suffix=' '+suffix
                        fields['copies']=dict(dest=cell.coordinate,value=match[2].strip(' _\t\u00a0'),
                                              label='Количество экземпляров',kind='number',prefix=prefix,suffix=suffix)
        finally:book.close()
        return fields
    return fields
