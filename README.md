# Генератор перевода

Инструмент для поиска переводимых строк в исходном коде и генерации XLIFF-файлов, которые затем можно отправлять в Crowdin или другой процесс локализации.

Сейчас проект поддерживает:
- CLI через `main.py`
- Windows-запуск через `app/start.cmd`
- Linux GUI через `app/start.sh`
- GitHub Actions для сборки и автоматической генерации исходных XLIFF в сторонних репозиториях

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

### Build workflow

Файл: `.github/workflows/build.yml`

Что делает:
- запускается на `push` и `pull_request` в `main` / `master`
- выполняется на runner label `homeserver`
- проверяет код через `compileall`
- запускает `python main.py --help`
- собирает Linux binary через PyInstaller
- публикует artifact `parser-linux`

### Dependabot

Файл: `.github/dependabot.yml`

Что обновляет:
- Python-зависимости из `requirements.txt`
- GitHub Actions

Частота: раз в неделю.

## Автоматическая генерация i18 для других репозиториев

Файлы:
- `.github/translation-repos.yml`
- `.github/workflows/generate-i18.yml`
- `scripts/generate_i18_repos.py`

Workflow читает список репозиториев из `.github/translation-repos.yml`, клонирует каждый репозиторий, находит его Crowdin-конфиг, генерирует исходные XLIFF-файлы, пушит ветку `i18-generated` и открывает PR в default branch.

### Формат `translation-repos.yml`

```yaml
repos:
  - name: DevCraft AdminPanel
    config: crowdin.yml
    repository: https://github.com/DevCraftClub/mhadmin.git
    source: upload/
```

Поля:
- `name` — произвольное имя для логов
- `config` — путь к Crowdin YAML внутри целевого репозитория
- `repository` — Git URL целевого репозитория
- `source` — каталог с исходным кодом, который нужно сканировать

### Как берутся пути генерации

Из Crowdin-конфига используется блок вида:

```yaml
files:
  - source: /upload/devcraft/locales/ru_RU/*.xliff
    translation: /upload/devcraft/locales/%locale_with_underscore%/%file_name%.%file_extension%
```

Из него вычисляется:
- каталог для `-o`: `upload/devcraft/locales`
- язык для `-l`: `ru_RU`
- модули для `-m`: имена существующих `*.xliff` в каталоге `ru_RU`

Поле `translation` не перезаписывается: workflow регенерирует только исходные XLIFF-файлы.

## Секрет `GH_PAT`

Для workflow `generate-i18.yml` нужен секрет `GH_PAT`.

`GH_PAT` = GitHub Personal Access Token, добавленный в:

`Settings -> Secrets and variables -> Actions -> New repository secret`

Почему нужен именно он:
- `GITHUB_TOKEN` действует только в текущем репозитории
- workflow пушит изменения и создаёт PR в других репозиториях из `.github/translation-repos.yml`

Минимально нужные права для fine-grained PAT:
- доступ ко всем целевым репозиториям из `.github/translation-repos.yml`
- `Contents: Read and write`
- `Pull requests: Read and write`
- `Metadata: Read`

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
  translation-repos.yml
  workflows/
    build.yml
    generate-i18.yml
scripts/
  generate_i18_repos.py
main.py
```
