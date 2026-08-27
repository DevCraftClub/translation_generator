# Генератор перевода

Инструмент для поиска переводимых строк в исходном коде и генерации XLIFF-файлов, которые затем можно отправлять в Crowdin или другой процесс локализации.

Сейчас проект поддерживает:
- CLI через `main.py`
- Windows-запуск через `app/start.cmd`
- Linux GUI через `app/start.sh`
- XLIFF с форматированием (pretty-print)

Сборка бинарников и генерация i18 для внешних репозиториев выполняются в отдельном репозитории **CrowdIn-Generator** (Woodpecker на `git.hrdr.dev`).

## Установка

```bash
pip install -r requirements.txt
```

Для Linux GUI дополнительно нужен GTK4 Python binding:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0
```

## Использование

### Linux GUI

Запуск:

```bash
./app/start.sh
```

GUI полностью на русском языке и использует ту же логику генерации, что и CLI.

### Windows

Для интерактивного запуска можно использовать:

```bat
app\start.cmd
```

Также в `app/` лежит собранный `app/_parser.exe`.

### CLI

```bash
python main.py -s /path/to/source -o /path/to/output -e /path/to/exclude -m messages -l ru_RU -d
```

### Параметры CLI

| Команда | Альтернатива | Описание |
| --- | --- | --- |
| `--source` | `-s` | Путь к исходным файлам, где искать переводимые строки |
| `--output` | `-o` | Путь к каталогу вывода без языкового кода |
| `--exception` | `-e` | Игнорируемые файлы или папки; параметр можно повторять |
| `--module` | `-m` | Имя выходного XLIFF-файла без расширения |
| `--lang` | `-l` | Исходный язык, например `ru_RU` |
| `--debug` | `-d` | Печатать traceback и ошибки обработки |

Итоговый файл сохраняется по пути:

```text
{output}/{lang}/{module}.xliff
```

## CI

### Dependabot

Файл: `.github/dependabot.yml`

Что обновляет:
- Python-зависимости из `requirements.txt`
- GitHub Actions

Частота: раз в неделю.

## Структура проекта

```text
assets/
  classes.py
  functions.py
  pipeline.py
app/
  start.cmd
  start.sh
  gui.py
.github/
  dependabot.yml
main.py
```
