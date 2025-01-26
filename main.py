import argparse
import os
import re
import time
import traceback
import xml.etree.cElementTree as ET
from pathlib import Path
from xml.dom import minidom


def list_dir(dirs, expt=None):
	"""Рекурсивная функция для поиска всех директорий и файлов."""
	# Используем множество (set) для expt, чтобы ускорить поиск
	expt = set(expt) if expt else set()
	result_dirs = []

	# os.scandir быстрее, поскольку предоставляет итератор
	for entry in os.scandir(dirs):
		if entry.is_dir():
			# Добавляем директории рекурсивно
			if entry.path not in expt:
				result_dirs.extend(list_dir(entry.path, expt))
		elif entry.path not in expt:
			# Добавляем файлы, которых нет в списке исключений
			result_dirs.append(entry.path)

	return result_dirs


# Print iterations progress
# https://stackoverflow.com/questions/3173320/text-progress-bar-in-terminal-with-block-characters
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
	"""
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
	percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
	filledLength = int(length * iteration // total)
	bar = fill * filledLength + '-' * (length - filledLength)
	print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
	# Print New Line on Complete
	if iteration == total:
		print()

def parse_arguments():
	"""Считывание и обработка аргументов командной строки."""
	parser = argparse.ArgumentParser(description='Генератор файлов перевода')
	parser.add_argument('-s', '--source', type=str, help='Путь к исходным файлам', default='source')
	parser.add_argument('-o', '--output', type=str, help='Путь к выходным файлам', default='output')
	parser.add_argument('-e', '--exception', type=str, help='Игнорируемые файлы/пути', action='append', default=[
		'engine/inc/maharder/admin/composer.lock',
		'engine/inc/maharder/admin/composer.phar',
		'engine/inc/maharder/admin/assets/',
		'engine/inc/maharder/_includes/composer',
		'engine/inc/maharder/_includes/module_files',
		'engine/inc/maharder/_includes/vendor',
		'engine/inc/maharder/admin/composer.json',
		'engine/inc/maharder/admin/.htaccess',
		'engine/inc/maharder/admin/assets/.htaccess',
		'engine/inc/maharder/admin/assets/js/i18n',
		'engine/inc/maharder/admin/assets/css',
		'engine/inc/maharder/admin/assets/img',
		'engine/inc/maharder/admin/assets/webfonts',
		'engine/inc/maharder/_locales',
		'engine/inc/maharder/_cache',
		'engine/inc/maharder/_logs',
		'engine/inc/maharder/_config',
		'engine/inc/maharder/_migrations',
	])
	parser.add_argument('-m', '--module', type=str, help='Имя файла перевода', default='messages')
	parser.add_argument('-l', '--lang', type=str, help='Язык перевода', default='ru_RU')
	parser.add_argument('-d', '--debug', action='store_true', help='Отображать ошибки', default=False)
	return parser.parse_args()


def sanitize_translations(message, translations):
	"""Проверка и добавление перевода в словарь."""
	if not message or message is None or message == '':  # Пропускаем пустые строки
		return ""
	if message not in translations:
		translations[message] = message  # Если нет перевода, используем оригинал
	return translations[message]

def extract_translations_from_file(file, regex_patterns, translations, debug, module):
	"""Извлечение сообщений перевода из файла."""
	try:
		with open(file, mode="r", encoding="utf-8") as f:
			for line in f:
				for regex in regex_patterns:
					match = re.search(regex, line)

					if match:
						# Убираем лишние кавычки сразу
						message = match.group("message").strip(' "\'')
						if message in ['', '#', '.', ',', module]:
							continue
						sanitize_translations(message, translations)
						# continue
	except Exception as e:
		if debug:
			print(f"Ошибка при обработке файла: {file}\n{str(e)}")
			traceback.print_exc()


def getTranslationsFromFile(output_file):
	"""Проверяет наличие файла перевода, возвращает dict с переводами или пустой dict."""
	translations = {}
	if not output_file.exists():
		return translations

	try:
		tree = ET.parse(output_file)
		root = tree.getroot()

		for trans_unit in root.findall(".//{urn:oasis:names:tc:xliff:document:1.2}trans-unit"):
			source = trans_unit.find("{urn:oasis:names:tc:xliff:document:1.2}source")
			target = trans_unit.find("{urn:oasis:names:tc:xliff:document:1.2}target")

			if source is not None and target is not None:
				translations[source.text] = target.text
	except Exception as e:
		print(f"Ошибка при чтении файла переводов: {output_file}\n{str(e)}")
		traceback.print_exc()

	return translations


def main():
	args = parse_arguments()

	# Определяем директории
	src_dir = Path(args.source).resolve()
	out_dir = Path(args.output).resolve() / args.lang
	out_dir.mkdir(parents=True, exist_ok=True)  # Создаем директорию, если отсутствует

	output_file = out_dir / f'{args.module}.xliff'
	translations = getTranslationsFromFile(output_file)  # Используем dict для перевода вместо списка
	exceptions = set(str(src_dir / e.strip()) for expt in args.exception for e in expt.split(','))

	# Ищем нужные файлы
	search_dirs = list_dir(src_dir, exceptions)

	regex_patterns = [
		# {{ 'Настройки' | trans }} или {% 'Настройки' | trans %}
		r"(?:{{|{%)[^'{]*'(?P<message>(?:[^']|\\')*?)'(?:\s*\|\s*\w+\s*)*\|\s*trans\s*(?:}}|%})",
        r"(?:{{|{%)[^\"{]*\"(?P<message>(?:[^\"]|\\\")*?)\"(?:\s*\|\s*\w+\s*)*\|\s*trans\s*(?:}}|%})",
		# __('module', 'message')
		r"__\(\s*\"(\s*\"(?P<message>.*?[^\\])\"\s*\)",
		r"__\(\s*'(\s*'(?P<message>.*?[^\\])'\s*\)",
		# {% trans %}message{% endtrans %}
		r"{%\s*trans\s*%}(?P<message>.*?){%\s*endtrans\s*%}",
		# 'text' | trans
		r"'(?P<message>(?:[^']|\\')*?)'(?:\s*\|\s*\w+\s*)*\|\s*trans",
		r"\"(?P<message>(?:[^\"]|\\\")*?)\"(?:\s*\|\s*\w+\s*)*\|\s*trans",
		# translate(`text`), __(`text`)
		r"translate\(`(?P<message>.*?)`\)",
		r"__\(`(?P<message>.*?)`\)",
		# translate("text"), __("text")
		r"translate\(\"(?P<message>[^\"]*?)\"\)",
		r"__\(\"(?P<message>[^\"]*?)\"\)",
		# translate('text'), __('text')
		r"translate\('(?P<message>(?:[^']|\\')*?)'\)",
		r"__\('(?P<message>(?:[^']|\\')*?)'\)"
	]

	# Печать прогресса
	printProgressBar(0, len(search_dirs), prefix='Сканирование файлов:', suffix='завершено', length=50)
	for i, filepath in enumerate(search_dirs):
		if Path(filepath).is_file():
			extract_translations_from_file(filepath, regex_patterns, translations, args.debug, args.module)
		time.sleep(0.1)  # Имитируем прогресс
		printProgressBar(i + 1, len(search_dirs), prefix='Сканирование файлов:', suffix='завершено', length=50)

	# Сохраняем переводы в XLIFF файл
	with open(output_file, 'w', encoding="utf-8") as f:
		xliff_tree = ET.Element("xliff", xmlns="urn:oasis:names:tc:xliff:document:1.2", version="1.2")
		file_tag = ET.SubElement(xliff_tree, "file", original=f'{args.module}.{args.lang}', datatype="plaintext")
		file_tag.set("source-language", args.lang)
		file_tag.set("target-language", args.lang)

		body = ET.SubElement(file_tag, "body")
		for id, (source, target) in enumerate(translations.items(), start=1):
			trans_unit = ET.SubElement(body, "trans-unit", id=str(id))
			ET.SubElement(trans_unit, "source").text = source
			ET.SubElement(trans_unit, "target").text = target

		f.write(minidom.parseString(ET.tostring(xliff_tree, encoding="unicode")).toprettyxml(indent="  "))


if __name__ == '__main__':
	main()
