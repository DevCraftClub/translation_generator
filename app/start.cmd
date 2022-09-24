@echo off
cls
setlocal EnableDelayedExpansion EnableExtensions
chcp 65001

set /p "source=Путь исходных файлов, для поиска фраз. Нажми ввод (Enter) для использования значения по умолчанию [src]:    " || set source=src
set /p "output=Путь выводимых файлов, куда будут сохраняться языковые файлы. Нажми ввод (Enter) для использования значения по умолчанию [out]:    " || set output=out
set /p "exception=Путь игнорируемых файлов, которые будут игнорироваться при проверке. Можно указать несколько путей, разделив их запятой (,). Нажми ввод (Enter) для использования значения по умолчанию []:    " || set exception=
set /p "plugin=Название файла перевода. Нажми ввод (Enter) для использования значения по умолчанию [messages]:    " || set plugin=messages
set /p "lang=Исходный язык. Нажми ввод (Enter) для использования значения по умолчанию [ru_RU]:    " || set lang=ru_RU
set /p "debug=Отображать ошибки при выполнении скрипта? [y/N]. Нажми ввод (Enter) для использования значения по умолчанию [N]:    " || set debug=n

echo ===============================================================

echo Путь исходных файлов: %source%
echo Путь выводимых файлов: %output%
echo Путь игнорируемых файлов: %exception%
echo Название файла перевода: %plugin%
echo Исходный язык: %lang%
echo Отображать ошибки при выполнении скрипта? %debug%

echo ===============================================================

set command_line=-s %source% -o %output% -m %plugin% -l %lang%

call :tolower debug

IF /i %debug% == y (
    set command_line=%command_line% -d True
)

IF /i "!exception!" NEQ "" (
    set command_line=%command_line% -e %exception%
)

echo %command_line%

start /b "" _parser.exe %command_line%

pause
endlocal


:tolower
for %%L IN (^^ a b c d e f g h i j k l m n o p q r s t u v w x y z) DO SET %1=!%1:%%L=%%L!
goto :EOF