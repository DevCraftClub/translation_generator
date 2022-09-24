import argparse
import os
import re
import time
import traceback
from pathlib import Path
import xml.etree.cElementTree as ET
from xml.dom import minidom
import numpy
import xmltodict


def list_dir(dirs, expt=None):
	if expt is None:
		expt = []
	_dirs = []

	for d in os.listdir(dirs):
		data = os.path.join(dirs, d)
		if Path(data).is_dir():
			if data not in expt:
				_dirs = [*_dirs, *list_dir(data, expt)]
		else:
			if data not in expt:
				_dirs.append(data)

	return _dirs


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

parser = argparse.ArgumentParser(description='Translation File Generator')

parser.add_argument('-s', '--source', type=str, help='Путь исходных файлов, для поиска фраз', default='src')
parser.add_argument('-o', '--output', type=str, help='Путь выводимых файлов, куда будут сохраняться языковые файлы', default='out')
parser.add_argument('-e', '--exception', type=str,  help='Путь игнорируемых файлов, которые будут игнорироваться при проверке', action='append',  default=[])
parser.add_argument('-m', '--module', type=str, help='Название файла перевода', default='messages')
parser.add_argument('-l', '--lang', type=str, help='Исходный язык', default='ru_RU')
parser.add_argument('-d', '--debug', type=bool, help='Отображать ошибки при выполнении скрипта?', default=False)

args = parser.parse_args()

if args.source == 'src':
	src_dir = os.path.join(os.path.dirname(__file__), args.source)
	Path(src_dir).mkdir(parents=True, exist_ok=True)
else:
	src_dir = args.source

if args.output == 'out':
	out_dir = os.path.join(os.path.dirname(__file__), args.output)
	Path(out_dir).mkdir(parents=True, exist_ok=True)
else:
	out_dir = args.output

output_file = os.path.join(out_dir, args.lang, f'{args.module}.xliff')
Path(os.path.join(out_dir, args.lang)).mkdir(parents=True, exist_ok=True)

translations = []
exceptions = []
for e in args.exception:
	for s in e.split(','):
		exceptions.append(s.strip())
search_dirs = list_dir(src_dir, exceptions)

regex = [
	r"{{[\s*][\'\"](?P<message>[^\|]*)[\'\"]\|trans[\s*\'\"]}}",
	r"{%[\s*][\'\"](?P<message>[^\|]*)[\'\"]\|trans[\s*\'\"]%}",
	r"{{[\s*][\'\"](?P<message>[^\|]*)[\'\"]\|htmlentities|raw|trans|html_entity_decode[\s*\'\"]}}",
	r"{%[\s*][\'\"](?P<message>[^\|]*)[\'\"]\|htmlentities|raw|trans|html_entity_decode[\s*\'\"]%}",
	r"\'(?P<message>[^\'\|]*)\'\|trans",
	r'\"(?P<message>[^\"\|]*)\"\|trans',
	r"\'(?P<message>[^\'\|]*)\'\|htmlentities|raw|trans|html_entity_decode",
	r'\"(?P<message>[^\"\|]*)\"\|htmlentities|raw|trans|html_entity_decode',
	r"{%\s*trans\s*%}(?P<message>[^{]*){%\s*endtrans\s*%}",
	r"__\([\s'\"](?P<module>.*)[\s'\"],[\s'\"](?P<message>.*)['\"]",
]

if Path(output_file).is_file():
	try:
		trans_file_parse = ET.tostring(ET.parse(output_file).getroot())
		trans_parsed_dict = xmltodict.parse(trans_file_parse)
		for v in trans_parsed_dict['ns0:xliff']['ns0:file']['ns0:body']['ns0:trans-unit']:
			translations.append({v['ns0:source']: v['ns0:target']})
	except Exception as exc:
		if args.debug:
			print(exc)
		else:
			pass

printProgressBar(0, len(search_dirs), prefix='Сканирование файлов:', suffix='завершено', length=50)

for i, f in enumerate(search_dirs):
	if Path(f).is_file():
		with open(f, mode="r", encoding="utf-8") as file:
			try:
				for l in file:
					for r in regex:
						result = re.findall(r, l)

						for rs in result:
							if isinstance(rs, (numpy.ndarray, list, tuple)): message = rs[-1]
							else: message = rs

							if message[0] == "'" or message[0] == '"': message = message[1:]
							if message[-1] == "'" or message[-1] == '"': message = message[:-1]

							if len(list(filter(lambda x: message in x, translations))) > 0:
								for tr in translations:
									try:
										for key, value in tr.iteritems():
											if key == message:
												if value != message:
													translations[key] = message
									except:
										for key, value in tr.items():
											if key == message:
												if value != message:
													translations[key] = message
							else:
								translations.append({message: message})
			except:
				if args.debug:
					print(f'File:\t{f}\nText:\t{l}')
					traceback.print_exc()
				else:
					pass
	time.sleep(0.1)
	printProgressBar(i + 1, len(search_dirs), prefix='Сканирование файлов:', suffix='завершено', length=50)

with open(output_file, 'w', encoding="utf-8") as f:
	xliff = ET.Element("xliff", xmlns="urn:oasis:names:tc:xliff:document:1.2", version="1.2")
	file = ET.SubElement(xliff, "file", original=f'{args.module}.{args.lang}', datatype="plaintext")
	file.set("source-language", args.lang)
	file.set("target-language", args.lang)
	body = ET.SubElement(file, "body")

	for i,t in enumerate(translations):
		c = i+1
		for k, v in t.items():
			transUnit = ET.SubElement(body, "trans-unit")
			transUnit.set("id", str(c))
			source = ET.SubElement(transUnit, "source").text = k
			target = ET.SubElement(transUnit, "target").text = v

	# f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
	xmlstr = minidom.parseString(ET.tostring(xliff, encoding="unicode")).toprettyxml(indent=f'\t')
	f.write(xmlstr)

if __name__ == '__main__':
	phrases_total = len(translations)
	print(f"""
===================================================
||\tАвтор:\t\tMaxim Harder <dev@devcraft.club>
||\tСайт:\t\thttps://devcraft.club
||\tTelegram:\thttps://t.me/MaHarder
||\t======================================
||\tApp:\t\tTranslations generator for Crowdin.com (For my Apps)
||\tВерсия:\t\t1.0.0
||\tДата:\t\t2022-09-15
||\tЛицензия:\tMIT
||\t======================================
||\tФраз:\t\t{phrases_total}
||\tИсходник:\t{args.source}
||\tВывод:\t\t{args.output}
||\tЯзык:\t\t{args.lang}
||\tПлагин:\t\t{args.module}
===================================================
""")
