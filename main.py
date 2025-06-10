import hashlib
import time
from pathlib import Path

from assets.classes import Body, File, TransUnit, Xliff
from assets.functions import (extract_translations_from_file, getTranslationsFromFile, list_dir, parse_arguments,
                              printProgressBar)


def main():
	args = parse_arguments()

	# Определяем директории
	src_dir = Path(args.source).resolve()
	out_dir = Path(args.output).resolve() / args.lang
	out_dir.mkdir(parents=True, exist_ok=True)
	output_file = out_dir / f'{args.module}.xliff'

	# Загружаем существующие переводы, если файл уже есть
	translations = getTranslationsFromFile(output_file)
	exceptions = set(str(src_dir / e.strip()) for expt in args.exception for e in expt.split(','))

	# Ищем файлы в исходной директории
	search_dirs = list_dir(src_dir, exceptions)

	regex_patterns = [
			r"(?:__|translate)\s*\(\s*([\"'`])(?P<message>(?:\\\1|.)*?)\1\s*[),]",
			r"(?:{{|{%)(?:[^'\"{}]|{[^{]})*['\"`](?P<message>(?:\\[`'\"]]|.)*?)[`'\"]][^|]*?\|\s*trans\s*(?:}}|%})",
			r"{%\s*trans\s*%}(?P<message>.*?){%\s*endtrans\s*%}",
			r"[\"'](?P<message>(?:\\[\"']|[^\"'])*?)[\"']\s*\|\s*trans\b",
	]

	printProgressBar(0, len(search_dirs), prefix='Сканирование файлов:', suffix='завершено', length=50)
	for i, filepath in enumerate(search_dirs):
		if Path(filepath).is_file():
			extract_translations_from_file(filepath, regex_patterns, translations, args.debug, args.module)
		time.sleep(0.1)  # Имитируем задержку для отображения прогресса
		printProgressBar(i + 1, len(search_dirs), prefix='Сканирование файлов:', suffix='завершено', length=50)

	# Формируем список объектов TransUnit на основе собранных переводов
	trans_units = []
	for source, target in translations.items():
		unit_id = hashlib.md5(source.encode("utf-8")).hexdigest()
		trans_units.append(TransUnit(id=unit_id, source=source, target=target))

	body = Body(trans_units=trans_units)
	file_obj = File(
			original=f"{args.module}.{args.lang}",
			datatype="plaintext",
			source_language=args.lang,
			target_language=args.lang,
			body=body
	)
	xliff_obj = Xliff(version="1.2", file=file_obj)

	# Сохранение в файл с использованием метода save_to_file
	xliff_obj.save_to_file(str(output_file))
	print(f"Файл сохранён как {output_file}")


if __name__ == '__main__':
	main()
