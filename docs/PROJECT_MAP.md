# Карта проекта

## Первые точки входа

| Задача | Где менять | Связанные части |
|---|---|---|
| Запуск | `Бюро ИД.cmd`, `app/workspace_preview.py` (`__main__`) | `studio.Studio`, `app/app_paths.py` |
| Главная, проекты, библиотека, дерево | `app/studio.py` | `app/project_analysis.py`, `app/folder_operations.py` |
| Панель задач при fullscreen | `app/taskbar_reveal.py` | нижняя зона 24px; маска окна, без изменения настроек Windows |
| Темы, иконки, подсказки, ленты | `app/ui_tools.py`, `app/command_icons.py`, `app/hints.py` | `app/app_dialogs.py`, `app/windows_integration.py` |
| Панели: отделить, скрыть, вернуть | `app/workspace_preview.py` (`pane_header`, `collapse_panel`, `restore_panel`) | `studio.build`, `app/save_decisions.py` |
| Перетягивание стеклянных панелей | `app/glass_resize.py` | `tests/verify_home_drag_release.py`, `tests/verify_glass_resize.py` |
| Поля ввода/выбор строки | `app/studio.py` (`visible_fields`, `queue_register_operation`) | `app/office_forms.py`, `app/act_layout.py` |
| Общие пути и локальная конфигурация | `app/app_paths.py` | `BUREAU_ID_DATA_DIR`, `BUREAU_ID_EXAMPLES_DIR` |
| Очередь Office и ответы | `workspace_preview.Session` | `app/PreviewWorker.ps1`; clean PDF перед review PDF, до двух тёплых сеансов |
| Excel: поля и перенос строк | `app/act_layout.py`, `app/ActFlow.ps1` | `data/act_anchors.json`, `app/BindExcel.ps1` |
| Excel: реестры, вставка/удаление | `app/RegisterRows.ps1` | `app/register_selection.py` — диапазон после позиции до шапки; `app/office_forms.py`, `app/MakeRegistry.ps1` |
| Word: распознавание и запись | `app/word_fields.py`, `app/WordFields.ps1` | `app/ConvertWord.ps1`, `app/manual_fields.py` |
| Ручные привязки | `app/manual_fields.py`, `app/manual_excel.py` | `app/InspectExcel.ps1`, `app/BindExcel.ps1` |
| Временный цвет PDF | `app/ReviewHighlight.ps1` | `Session.review_pdf`; `latest` всегда чистый |
| Быстрый слой / итоговый кэш | `app/fast_preview.py`, `app/final_pdf_cache.py` | `docs/HYBRID_EDITOR.md`; Canvas только для просмотра, кэш только для подтверждённых файлов |
| Проверка формул | `app/FormulaValidation.ps1` | PreviewWorker, MakeRegistry; контрольные тесты реестров |
| Крупные PDF-схемы / плитки | `app/pdf_tiles.py` | `tests/verify_pdf_tiles.py`, `docs/PDF_VIEWER_PLAN.md` |
| Просмотр PDF | `app/pdf_page_preview.py` | `app/pdf_renderer.py` → отдельный `app/pdf_render_worker.py` |
| Выделение/OCR PDF-текста | `app/pdf_text_selection.py` | `app/PassportOCR.ps1` |
| Ctrl+C/V/X/Z/Y, выделение, колесо | `app/clipboard_keys.py`, `app/drag_selection.py`, `app/interactions.py`, `app/auto_scroll.py` | `app/keyboard_navigation.py` |
| Паспорта и сертификаты | `app/scanner_ui.py`, `app/passports.py` | `app/quality_library.py`, `app/PassportOCR.ps1` |
| Комплект для печати | `app/package_build.py`, `app/package_checks.py` | `app/MakeRegistry.ps1`, `Session` |
| Сохранить / не сохранять | `app/save_decisions.py`, `app/recovery_state.py` | `.recovery/baseline`, `working`, `checkpoints`, `.backups` внутри проекта |
| Drag-and-drop файлов | `app/win_drop.py` | `vendor/tkdnd-win-x64/` |
| Проверки | `tools/check_project.py`, `verify_*.py` | `docs/DEVELOPMENT.md` |
| GitHub и локальная история | `tools/github_bundle.py` | `docs/SYNC.md`, `.git/codex-sync/` |

## Каталоги

- Корень: запуск «Бюро ИД», README, инструкции агента и списки зависимостей.
- `app/`: рабочие Python-модули и Office PowerShell workers; их относительные связи сохранены.
- `tests/`: проверки; запуск через `python tools/run_check.py имя_проверки.py`.
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
