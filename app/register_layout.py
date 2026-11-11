"""Recognize register columns from their printed headers."""
import re
from openpyxl import load_workbook


def register_fields(path):
    book = load_workbook(path, data_only=False)
    sheet = book.active
    try:
        for row in sheet.iter_rows(max_row=min(30, sheet.max_row)):
            headings = {cell.column: ' '.join(str(cell.value or '').lower().split()) for cell in row}
            title = next((c for c,v in headings.items() if v.startswith('наименование')), None)
            ordinal = next((c for c,v in headings.items() if re.search(r'№\s*п\s*[./]\s*п',v)), None)
            if title and ordinal == 1:
                header = row[0].row
                break
        else:
            return {}
        footer = next((r for r in range(header+1,sheet.max_row+1)
                       if re.match(r'^(передал|принял|сдал|сдача|приемка|приёмка)',
                                   str(sheet.cell(r,ordinal).value or '').strip(),re.I)), None)
        if footer is None:
            return {}
        columns = {}
        for c,v in headings.items():
            if c==ordinal or not v:
                continue
            if 'страниц' in v and ('кол' in v or 'число' in v) or 'лист' in v and ('кол' in v or 'число' in v):
                columns[c] = ('Количество листов','number')
            elif ('лист' in v or 'страниц' in v) and ('порядков' in v or 'сквоз' in v or 'по порядку' in v or 'по списку' in v or v.startswith('№ страниц')):
                continue
            elif 'дата' in v:
                columns[c] = ('Дата','datecell')
            else:
                columns[c] = (str(sheet.cell(header,c).value).strip(),'text')
        result = {}
        def header_field(key, coordinate, label, span=None):
            cell = sheet[coordinate]
            result[key] = dict(dest=coordinate, value=str(cell.value or ''), label=label, kind='text', prefix='')
            if span:
                result[key]['span'] = span

        # Two known register headers; their table columns are resolved separately.
        if str(sheet['A2'].value or '').strip() == 'Заказчик:' and str(sheet['D4'].value or '').strip() == 'Шифр проекта:':
            for key, coordinate, label in [('regClient','B2','Заказчик'), ('regBuilder','B4','Подрядчик'),
                                           ('regAddress','E2','Объект и адрес'), ('regProject','E4','Шифр проекта')]:
                header_field(key,coordinate,label,coordinate+':C'+coordinate[1:] if coordinate.startswith('B') and sheet['C'+coordinate[1:]].value is None else None)
        if str(sheet['A1'].value or '').strip() == 'Заказчик' and str(sheet['H8'].value or '').strip() == 'Проект:':
            for key, coordinate, label in [('regClient','A2','Заказчик'), ('regPostal','I1','Адрес'),
                                           ('regAddress','I4','Объект'), ('regProject','I8','Проект')]:
                header_field(key,coordinate,label)
            if all(sheet.cell(5,c).value is None for c in range(2,7)):
                header_field('regBuilder','A5','Генподрядчик','A5:F5')
        for r in range(header+1,footer):
            first=sheet.cell(r,ordinal)
            if first.value and any(area.min_row==r and area.min_col==ordinal and area.max_col>=max(columns) for area in sheet.merged_cells.ranges):
                value=str(first.value)
                group=bool(re.match(r'^(АОСР|АООК|Акты|Исполнительные схемы|Паспорта|Сертификаты|Приложения)',value,re.I))
                result[('group' if group else 'part')+str(r)]=dict(dest=first.coordinate,value=value,label='Группа документов' if group else 'Раздел комплекта',kind='text',prefix='')
                continue
            title_cell=sheet.cell(r,title)
            if title_cell.__class__.__name__=='MergedCell':continue
            if title_cell.value is None and not title_cell.border.bottom.style:continue
            for c,(label,kind) in columns.items():
                cell=sheet.cell(r,c)
                if cell.__class__.__name__=='MergedCell' or cell.data_type=='f':
                    continue
                if not cell.has_style and cell.value is None:
                    continue
                value=cell.value
                if hasattr(value,'strftime'):
                    value=value.strftime('%d.%m.%Y')
                result[f'row{r}_{c}']=dict(dest=cell.coordinate,value=str(value if value is not None else ''),
                                          label=label,kind=kind,prefix='')
        return result
    finally:
        book.close()
