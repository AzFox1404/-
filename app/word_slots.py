"""Empty slots in known forms, located by permanent surrounding wording."""
import re


def supplement(kind, texts, fields, add, has_image=False, font_sizes=None):
    def slot(key, label, i, a, b, date=False):
        if key in fields:
            return
        add(key, label, [(i, a, b)], 'worddate' if date else 'text')
        if key in fields and a == b:
            part = fields[key]['segments'][0]
            if a and (texts[i][a-1].isalnum() or texts[i][a-1]==':'):
                part['prefix'] = ' '
            if b < len(texts[i]) and texts[i][b].isalnum():
                part['suffix'] = ' '
        if date and key in fields and not fields[key]['value'].strip():
            fields[key]['sample'] = '01.01.2000'

    if kind == 'order':
        for i, value in enumerate(texts):
            if not has_image and value.strip().lower() == 'общество с ограниченной ответственностью':
                for offset, key, label in [(1,'orderIssuer','Организация, издавшая приказ'), (2,'orderRequisites','Реквизиты организации')]:
                    if i+offset<len(texts) and not texts[i+offset].strip():
                        slot(key,label,i+offset,0,len(texts[i+offset]))
                        if key in fields:
                            fields[key]['segments'][0]['fontSize'] = (font_sizes or {}).get(i,12)
            match = re.match(r'\s*Приказ\s*№\s*(.*)$', value, re.I)
            if match:
                slot('orderNumber', 'Номер приказа', i, match.start(1), match.end(1))
                if i+1 < len(texts) and texts[i+1].strip() in ('', 'г.'):
                    slot('orderDate', 'Дата приказа', i+1, 0, len(texts[i+1]), True)
                    fields['orderDate']['value'] = ''
                    fields['orderDate']['segments'][0]['sample'] = '01.01.2000 г.'
            match = re.search(r'на\s+Объекте:\s*(.*?)\s*,\s*расположенн\w*\s+по адресу:\s*(.*?)\s*$', value, re.I)
            if match:
                slot('orderObject', 'Объект приказа', i, match.start(1), match.end(1))
                end = match.end(2)
                if value[match.start(2):end].strip() == '.':
                    end = match.start(2)
                slot('orderAddress', 'Адрес объекта', i, match.start(2), end)
            match = re.match(r'\s*Назначить\s+(.*?),\s*производителя работ\s*\n(.*?),\s*(?:ответственным|уполномоченным)', value, re.I | re.S)
            if match:
                slot('orderAppointee', 'Назначаемое лицо · ФИО в форме документа', i, match.start(1), match.end(1))
                slot('orderEmployer', 'Организация назначаемого лица', i, match.start(2), match.end(2))
            match = re.match(r'\s*(Генеральный директор|Производитель работ)(\s{3,})(.*)$', value, re.I)
            if match:
                key = 'orderDirector' if match[1].lower().startswith('генеральный') else 'orderAcknowledged'
                slot(key, match[1]+' · ФИО', i, match.start(2), len(value))
                if key in fields:
                    fields[key]['segments'][0]['prefix'] = '    '
                    fields[key]['value'] = fields[key]['value'].strip()
            if value.strip() == 'С приказом ознакомлен:' and i+1 < len(texts) and not texts[i+1].strip():
                slot('orderAcknowledged', 'Ознакомлен · должность и ФИО', i+1, 0, len(texts[i+1]))

    if kind in ('quality', 'registry'):
        for i, value in enumerate(texts):
            match = re.match(r'\s*(Приложение|Реестр документов качества)\s*№\s*(.*)$', value, re.I)
            if match:
                key = 'appendixNumber' if match[1].lower() == 'приложение' else 'qualityNumber'
                slot(key, 'Номер приложения' if key == 'appendixNumber' else 'Номер реестра качества', i, match.start(2), match.end(2))
            match = re.match(r'к Акту\s*(.*?)\s+от\s+(.*?)\s+освидетельствования скрытых работ(.*?)\s+по адресу:\s*(.*)$', value, re.I)
            if match:
                for n, key, label in [(1, 'actRef', 'Номер связанного акта'), (2, 'refDate', 'Дата связанного акта'),
                                      (3, 'refWork', 'Работы / конструкции связанного акта'), (4, 'regAddress', 'Объект и адрес')]:
                    slot(key, label, i, match.start(n), match.end(n), n == 2)

    if kind == 'act':
        for i, value in enumerate(texts):
            if value.strip() == '№' and i+1 < len(texts) and not texts[i+1].strip():
                slot('number', 'Номер акта', i+1, 0, len(texts[i+1]))
            if value.strip().lower().startswith('полное и (или)') and 'саморегулируемой организации' in value and i and not texts[i-1].strip():
                slot('sro'+str(i-1), 'СРО · реквизиты', i-1, 0, len(texts[i-1]))
            if re.search(r'произвели осмотр.*выполненных\s*:?\s*$', value, re.I) and i+1 < len(texts) and not texts[i+1].strip():
                slot('executor', 'Исполнитель работ', i+1, 0, len(texts[i+1]))
        # Split date cells retain quotation marks and the printed year suffix.
        for i in range(len(texts)-6):
            if texts[i].strip() != '«' or texts[i+2].strip() != '»':
                continue
            if texts[i+1].strip() or texts[i+3].strip() or texts[i+5].strip() != '20' or texts[i+6].strip() != 'г.':
                continue
            context = ' '.join(texts[max(0, i-5):i]).lower()
            key, label = ('workStart', 'Начало работ') if 'начала работ' in context else ('workEnd', 'Окончание работ') if 'окончания работ' in context else ('actDate', 'Дата акта')
            if key in fields:
                continue
            add(key, label, [(j, 0, len(texts[j])) for j in (i+1, i+3, i+5)], 'worddate')
            # add() normally drops empty continuations; these three cells are one date.
            if key in fields and len(fields[key]['segments']) == 3:
                fields[key]['value'] = ''
                for part, sample in zip(fields[key]['segments'], ('01', 'января', '2000')):
                    part['sample'] = sample
