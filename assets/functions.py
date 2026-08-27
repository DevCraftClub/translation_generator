import argparse
import os
import re
import traceback
import xml.etree.cElementTree as ET
from pathlib import Path
from xml.dom import minidom

# Один PHP-строковый литерал в одинарных/двойных/обратных кавычках,
# с корректной обработкой экранированных символов внутри.
PHP_STRING_LITERAL = r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`"
PHP_LITERAL_RE = re.compile(PHP_STRING_LITERAL, re.DOTALL)

# Часть конкатенации: строковый литерал или PHP_EOL (вставляется как \n).
PHP_CONCAT_PART = rf"(?:{PHP_STRING_LITERAL}|PHP_EOL)"

# Аргумент вызова __()/translate()/t(): один литерал либо цепочка конкатенации
# ('a' . 'b' . PHP_EOL . 'c'), включая многострочные варианты.
CALL_MESSAGE_PATTERN = (
		rf"(?:__|translate|\bt)\s*\(\s*"
		rf"(?P<message>(?:{PHP_CONCAT_PART})(?:\s*\.\s*(?:{PHP_CONCAT_PART}))*)"
		rf"\s*[),]"
)


def get_regex_patterns():
	"""Возвращает паттерны поиска переводимых строк."""
	return [
			CALL_MESSAGE_PATTERN,
			r"(?:{{|{%)(?:[^'\"{}]|{[^{]})*['\"`](?P<message>(?:\\[`'\"]]|.)*?)[`'\"]][^|]*?\|\s*trans\s*(?:}}|%})",
			r"{%\s*trans\s*%}(?P<message>.*?){%\s*endtrans\s*%}",
			r"[\"'](?P<message>(?:\\[\"']|[^\"'])*?)[\"']\s*\|\s*trans\b",
	]


def concat_php_literals(raw):
	"""Склеивает конкатенированные PHP-литералы/'PHP_EOL' ('a' . PHP_EOL . 'b') в одну строку."""
	parts = []
	for m in re.finditer(PHP_CONCAT_PART, raw, re.DOTALL):
		tok = m.group(0)
		parts.append("\n" if tok == "PHP_EOL" else tok[1:-1])
	return "".join(parts)


def list_dir(dirs, expt=None):
	"""Рекурсивная функция для поиска всех директорий и файлов."""
	expt = set(expt) if expt else set()
	result_dirs = []
	for entry in os.scandir(dirs):
		if entry.is_dir():
			if entry.path not in expt:
				result_dirs.extend(list_dir(entry.path, expt))
		elif entry.path not in expt:
			result_dirs.append(entry.path)
	return result_dirs


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
	"""
	Вывод индикатора прогресса в консоль.
	"""
	if total <= 0:
		print(f'\r{prefix} |{"-" * length}| 100.0% {suffix}', end=printEnd)
		if printEnd != "":
			print()
		return
	percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
	filledLength = int(length * iteration // total)
	bar = fill * filledLength + '-' * (length - filledLength)
	print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
	if iteration == total:
		print()


def parse_arguments():
	"""Считывание и обработка аргументов командной строки."""
	parser = argparse.ArgumentParser(description='Генератор файлов перевода')
	parser.add_argument('-s', '--source', type=str, help='Путь к исходным файлам', default=r'source')
	parser.add_argument('-o', '--output', type=str, help='Путь к выходным файлам', default=r'output')
	parser.add_argument('-e', '--exception', type=str, help='Игнорируемые файлы/пути', action='append', default=[
			'devcraft/configs',
			'devcraft/logs',
			'devcraft/cache',
			'devcraft/vendor',
			'devcraft/composer.json',
	])
	parser.add_argument('-m', '--module', type=str, help='Имя файла перевода', default='messages')
	parser.add_argument('-l', '--lang', type=str, help='Язык перевода', default='ru_RU')
	parser.add_argument('-d', '--debug', action='store_true', help='Отображать ошибки', default=False)
	return parser.parse_args()


def sanitize_translations(message, translations):
	"""Проверка и добавление перевода в словарь."""
	if not message or message is None or message == '':
		return ""
	if message not in translations:
		translations[message] = message  # Если нет перевода, используем оригинал
	return translations[message]


def _register_message(message, translations, module):
	"""Пропускает пустые/служебные строки, снимает экранирование кавычек и сохраняет перевод."""
	if not message or message in {'#', '.', ',', module, '=&gt;', '=&lt;', '&gt;', '&lt;'}:
		return
	message = re.sub(r"\\(['\"`])", r"\1", message)
	sanitize_translations(message, translations)


def extract_translations_from_file(file, regex_patterns, translations, debug, module):
	"""
	Извлечение сообщений перевода из файла.

	regex_patterns[0] (вызовы __()/translate()/t()) сканируется по всему файлу
	целиком: иначе многострочная конкатенация ('a' . 'b' . ...) никогда не
	совпадает — построчный поиск видит только один фрагмент за раз.

	Остальные паттерны (twig-фильтры |trans, {% trans %}) сканируются
	построчно, как раньше: их регулярки не рассчитаны на весь файл и при
	поиске по всему тексту могут "перескочить" через границы строк.
	"""
	call_pattern = re.compile(regex_patterns[0], re.DOTALL)
	line_patterns = [re.compile(p, re.DOTALL) for p in regex_patterns[1:]]
	try:
		with open(file, mode="r", encoding="utf-8") as f:
			content = f.read()

		for match in call_pattern.finditer(content):
			message = concat_php_literals(match.group("message")).strip()
			_register_message(message, translations, module)

		for line in content.splitlines():
			for regex in line_patterns:
				match = regex.search(line)
				if match:
					message = match.group("message").strip().strip('"\'`')
					_register_message(message, translations, module)
					break
	except Exception as e:
		if debug:
			print(f"Ошибка при обработке файла: {file}\n{str(e)}")
			traceback.print_exc()


def getTranslationsFromFile(output_file):
	"""
	Проверяет наличие файла переводов и возвращает словарь с переводами.
	"""
	translations = {}
	if not output_file.exists():
		return translations
	try:
		tree = ET.parse(output_file)
		root = tree.getroot()
		ns = {'xliff': 'urn:oasis:names:tc:xliff:document:1.2'}
		for trans_unit in root.findall(".//xliff:trans-unit", ns):
			source = trans_unit.find("xliff:source", ns)
			target = trans_unit.find("xliff:target", ns)
			if source is not None and target is not None:
				translations[source.text] = target.text
	except Exception as e:
		print(f"Ошибка при чтении файла переводов: {output_file}\n{str(e)}")
		traceback.print_exc()
	return translations


def prettify_xliff(file_path):
	"""Перезаписывает XLIFF с отступами (не в одну строку)."""
	path = Path(file_path)
	raw = path.read_bytes()
	dom = minidom.parseString(raw)
	pretty = dom.toprettyxml(indent="\t", encoding="utf-8")
	# minidom adds an extra XML declaration line; keep one declaration + body
	text = pretty.decode("utf-8")
	lines = [line for line in text.splitlines() if line.strip()]
	if lines and lines[0].startswith("<?xml"):
		body = "\n".join(lines[1:])
		path.write_text(f'{lines[0]}\n{body}\n', encoding="utf-8")
	else:
		path.write_text("\n".join(lines) + "\n", encoding="utf-8")
	return path
