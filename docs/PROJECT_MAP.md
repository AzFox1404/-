# Карта проекта

## Первые точки входа

| Задача | Где менять | Связанные части |
|---|---|---|
| Запуск | `Открыть редактор.cmd`, `workspace_preview.py` (`__main__`) | `studio.Studio`, `app_paths.py` |
| Главная, проекты, библиотека, дерево | `studio.py` | `project_analysis.py`, `folder_operations.py` |
| Темы, иконки, подсказки, ленты | `ui_tools.py`, `command_icons.py`, `hints.py` | `app_dialogs.py`, `windows_integration.py` |
| Панели: отделить, скрыть, вернуть | `workspace_preview.py` (`pane_header`, `collapse_panel`, `restore_panel`) | `studio.build`, `save_decisions.py` |
| Перетягивание стеклянных панелей | `glass_resize.py` | `verify_home_drag_release.py`, `verify_glass_resize.py` |
| Поля ввода/выбор строки | `studio.py` (`visible_fields`, `queue_register_operation`) | `office_forms.py`, `act_layout.py` |
| Общие пути и локальная конфигурация | `app_paths.py` | `BUREAU_ID_DATA_DIR`, `BUREAU_ID_EXAMPLES_DIR` |
| Очередь Office и ответы | `workspace_preview.Session` | `PreviewWorker.ps1` |
| Excel: поля и перенос строк | `act_layout.py`, `ActFlow.ps1` | `data/act_anchors.json`, `BindExcel.ps1` |
| Excel: реестры, вставка/удаление | `RegisterRows.ps1` | `office_forms.py`, `MakeRegistry.ps1` |
| Word: распознавание и запись | `word_fields.py`, `WordFields.ps1` | `ConvertWord.ps1`, `manual_fields.py` |
| Ручные привязки | `manual_fields.py`, `manual_excel.py` | `InspectExcel.ps1`, `BindExcel.ps1` |
| Временный цвет PDF | `ReviewHighlight.ps1` | `Session.review_pdf`; `latest` всегда чистый |
| Просмотр PDF | `pdf_page_preview.py` | `pdf_renderer.py` → отдельный `pdf_render_worker.py` |
| Выделение/OCR PDF-текста | `pdf_text_selection.py` | `PassportOCR.ps1` |
| Ctrl+C/V/X/Z/Y, выделение, колесо | `clipboard_keys.py`, `drag_selection.py`, `interactions.py`, `auto_scroll.py` | `keyboard_navigation.py` |
| Паспорта и сертификаты | `scanner_ui.py`, `passports.py` | `quality_library.py`, `PassportOCR.ps1` |
| Комплект для печати | `package_build.py`, `package_checks.py` | `MakeRegistry.ps1`, `Session` |
| Сохранить / не сохранять | `save_decisions.py`, `recovery_state.py` | `.recovery`, `.backups` внутри проекта |
| Drag-and-drop файлов | `win_drop.py` | `vendor/tkdnd-win-x64/` |
| Проверки | `tools/check_project.py`, `verify_*.py` | `docs/DEVELOPMENT.md` |
| GitHub и локальная история | `tools/github_bundle.py` | `docs/SYNC.md`, `.git/codex-sync/` |

## Каталоги

- Корень: рабочие Python-модули, Office PowerShell workers, проверки. Расположение пока сохранено для совместимости.
- `docs/`: краткие общие требования, текущее состояние и регламент разработки.
- `tools/`: лёгкие служебные проверки и обмен с GitHub.
- `data/`: только обезличенные постоянные подписи форм, не сами заполненные документы.
- `vendor/`: TkDND с исходной лицензией и библиотекой для Windows x64.
- `examples/`: описание подключения собственных тестовых документов; реальные документы игнорируются.
- `review/`: локальные результаты исследований; в Git только два воспроизводимых PowerShell-проверяющих скрипта.
- `Рабочая папка ИД/`: **локальные данные**: проекты, библиотека, настройки, черновики, кэш OCR. Не синхронизировать с кодом.
- `Рабочие копии/`, `Пример выгрузки/`, `.local_notes/`: локальные материалы, не публикуются.

## Движение данных

`источник → project_analysis → поля Word/Excel → Session → PreviewWorker → чистый файл + чистый PDF + review PDF → PDF renderer process → Tk`

`каталог документов качества → выбранные записи → акт/приложение → package_build → титул + реестр + акты/приложения + паспорта`

`git status → проверка remote main → правка → нужные проверки → commit/API publish → проверка SHA → синхронная локальная main`

Не перечитывать весь проект: начните с одной строки этой таблицы, затем найдите функцию через `rg`.
