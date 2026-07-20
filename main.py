import time

from assets.functions import parse_arguments, printProgressBar
from assets.pipeline import run_generator


def main():
	args = parse_arguments()

	def on_progress(current, total):
		printProgressBar(current, total, prefix='Сканирование файлов:', suffix='завершено', length=50)
		if total > 0:
			time.sleep(0.1)

	output_file = run_generator(
			source=args.source,
			output=args.output,
			module=args.module,
			lang=args.lang,
			exceptions=args.exception,
			debug=args.debug,
			progress=on_progress,
	)
	print(f"Файл сохранён как {output_file}")


if __name__ == '__main__':
	main()
