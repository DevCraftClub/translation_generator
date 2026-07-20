import hashlib
from pathlib import Path

from assets.classes import Body, File, TransUnit, Xliff
from assets.functions import (
	getTranslationsFromFile,
	get_regex_patterns,
	list_dir,
	extract_translations_from_file,
)


def run_generator(
		source,
		output,
		module="messages",
		lang="ru_RU",
		exceptions=None,
		debug=False,
		progress=None,
):
	src_dir = Path(source).resolve()
	out_dir = Path(output).resolve() / lang
	out_dir.mkdir(parents=True, exist_ok=True)
	output_file = out_dir / f"{module}.xliff"

	translations = getTranslationsFromFile(output_file)
	exception_paths = _normalize_exceptions(src_dir, exceptions or [])
	search_paths = list_dir(src_dir, exception_paths)
	regex_patterns = get_regex_patterns()

	if progress is not None:
		progress(0, len(search_paths))

	for index, filepath in enumerate(search_paths, start=1):
		if Path(filepath).is_file():
			extract_translations_from_file(filepath, regex_patterns, translations, debug, module)
		if progress is not None:
			progress(index, len(search_paths))

	trans_units = []
	for source_text, target_text in translations.items():
		unit_id = hashlib.md5(source_text.encode("utf-8")).hexdigest()
		trans_units.append(TransUnit(id=unit_id, source=source_text, target=target_text))

	xliff_obj = Xliff(
			version="1.2",
			file=File(
					original=f"{module}.{lang}",
					datatype="plaintext",
					source_language=lang,
					target_language=lang,
					body=Body(trans_units=trans_units),
			),
	)
	xliff_obj.save_to_file(str(output_file))
	return output_file


def _normalize_exceptions(src_dir, exceptions):
	normalized = set()
	for value in exceptions:
		for item in str(value).split(","):
			candidate = item.strip()
			if not candidate:
				continue
			path = Path(candidate)
			if not path.is_absolute():
				path = src_dir / path
			normalized.add(str(path.resolve(strict=False)))
	return normalized
