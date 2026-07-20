from pathlib import Path
import threading
import traceback

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk

from assets.pipeline import run_generator


ROOT_DIR = Path(__file__).resolve().parents[1]


class TranslationWindow(Gtk.ApplicationWindow):
	def __init__(self, app):
		super().__init__(application=app, title="Генератор перевода")
		self.set_default_size(860, 620)

		self._start_button = None
		self._progress_bar = None
		self._status_label = None
		self._source_entry = None
		self._output_entry = None
		self._exception_entry = None
		self._module_entry = None
		self._lang_entry = None
		self._debug_switch = None
		self._log_buffer = None
		self._build_ui()

	def _build_ui(self):
		root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
		root_box.set_margin_top(16)
		root_box.set_margin_bottom(16)
		root_box.set_margin_start(16)
		root_box.set_margin_end(16)

		header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
		logo = Gtk.Picture.new_for_filename(str(ROOT_DIR / "assets" / "icon.png"))
		logo.set_size_request(72, 72)
		header_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
		title = Gtk.Label(label="Генератор перевода")
		title.set_xalign(0)
		title.add_css_class("title-2")
		subtitle = Gtk.Label(label="Создание XLIFF-файлов из исходного кода")
		subtitle.set_xalign(0)
		subtitle.add_css_class("dim-label")
		header_text.append(title)
		header_text.append(subtitle)
		header_box.append(logo)
		header_box.append(header_text)
		root_box.append(header_box)

		form = Gtk.Grid(column_spacing=12, row_spacing=12)
		form.set_hexpand(True)

		self._source_entry = Gtk.Entry(text="src")
		self._output_entry = Gtk.Entry(text="out")
		self._exception_entry = Gtk.Entry()
		self._module_entry = Gtk.Entry(text="messages")
		self._lang_entry = Gtk.Entry(text="ru_RU")
		self._debug_switch = Gtk.Switch(active=False)

		self._attach_row(form, 0, "Путь исходных файлов", self._source_entry, "Выбрать", self._on_pick_source)
		self._attach_row(form, 1, "Путь выводимых файлов", self._output_entry, "Выбрать", self._on_pick_output)
		self._attach_row(form, 2, "Путь игнорируемых файлов", self._exception_entry, "Добавить", self._on_pick_exception)
		self._attach_row(form, 3, "Название файла перевода", self._module_entry)
		self._attach_row(form, 4, "Исходный язык", self._lang_entry)

		debug_label = Gtk.Label(label="Отображать ошибки")
		debug_label.set_xalign(0)
		form.attach(debug_label, 0, 5, 1, 1)
		form.attach(self._debug_switch, 1, 5, 1, 1)

		root_box.append(form)

		self._start_button = Gtk.Button(label="Запустить")
		self._start_button.connect("clicked", self._on_start)
		root_box.append(self._start_button)

		self._progress_bar = Gtk.ProgressBar(show_text=True)
		self._progress_bar.set_text("Ожидание запуска")
		root_box.append(self._progress_bar)

		self._status_label = Gtk.Label(label="Сканирование файлов не запущено")
		self._status_label.set_xalign(0)
		root_box.append(self._status_label)

		log_label = Gtk.Label(label="Журнал")
		log_label.set_xalign(0)
		root_box.append(log_label)

		self._log_buffer = Gtk.TextBuffer()
		log_view = Gtk.TextView(buffer=self._log_buffer, editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
		scroll = Gtk.ScrolledWindow()
		scroll.set_vexpand(True)
		scroll.set_child(log_view)
		root_box.append(scroll)

		self.set_child(root_box)

	def _attach_row(self, grid, row, label_text, entry, button_text=None, handler=None):
		label = Gtk.Label(label=label_text)
		label.set_xalign(0)
		grid.attach(label, 0, row, 1, 1)

		box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
		entry.set_hexpand(True)
		box.append(entry)
		if button_text and handler:
			button = Gtk.Button(label=button_text)
			button.connect("clicked", handler)
			box.append(button)
		grid.attach(box, 1, row, 1, 1)

	def _on_pick_source(self, _button):
		self._select_folder(self._source_entry)

	def _on_pick_output(self, _button):
		self._select_folder(self._output_entry)

	def _on_pick_exception(self, _button):
		self._select_folder(self._exception_entry, append=True)

	def _select_folder(self, entry, append=False):
		if hasattr(Gtk, "FileDialog"):
			dialog = Gtk.FileDialog(title="Выберите папку")
			dialog.select_folder(self, None, self._on_folder_selected, (entry, append))
			return

		dialog = Gtk.FileChooserNative(
				title="Выберите папку",
				transient_for=self,
				action=Gtk.FileChooserAction.SELECT_FOLDER,
				accept_label="Выбрать",
				cancel_label="Отмена",
		)
		dialog.connect("response", self._on_native_folder_response, entry, append)
		dialog.show()

	def _on_folder_selected(self, dialog, result, user_data):
		entry, append = user_data
		try:
			folder = dialog.select_folder_finish(result)
		except GLib.Error:
			return
		self._apply_folder_selection(entry, folder, append)

	def _on_native_folder_response(self, dialog, response, entry, append):
		try:
			if response == Gtk.ResponseType.ACCEPT:
				folder = dialog.get_file()
				self._apply_folder_selection(entry, folder, append)
		finally:
			dialog.destroy()

	def _apply_folder_selection(self, entry, folder, append):
		if folder is None:
			return
		path = folder.get_path() or folder.get_uri()
		if append and entry.get_text().strip():
			entry.set_text(f"{entry.get_text().strip()},{path}")
		else:
			entry.set_text(path)

	def _on_start(self, _button):
		self._start_button.set_sensitive(False)
		self._progress_bar.set_fraction(0.0)
		self._progress_bar.set_text("Подготовка")
		self._status_label.set_text("Запуск обработки…")
		self._set_log("")
		worker = threading.Thread(target=self._run_generation, daemon=True)
		worker.start()

	def _run_generation(self):
		try:
			output_file = run_generator(
					source=self._source_entry.get_text().strip(),
					output=self._output_entry.get_text().strip(),
					module=self._module_entry.get_text().strip() or "messages",
					lang=self._lang_entry.get_text().strip() or "ru_RU",
					exceptions=[self._exception_entry.get_text().strip()] if self._exception_entry.get_text().strip() else [],
					debug=self._debug_switch.get_active(),
					progress=self._report_progress,
			)
		except Exception as exc:
			message = traceback.format_exc() if self._debug_switch.get_active() else str(exc)
			GLib.idle_add(self._finish_with_error, message)
			return
		GLib.idle_add(self._finish_success, str(output_file))

	def _report_progress(self, current, total):
		GLib.idle_add(self._update_progress, current, total)

	def _update_progress(self, current, total):
		if total <= 0:
			self._progress_bar.set_fraction(1.0)
			self._progress_bar.set_text("Файлы не найдены, создан пустой XLIFF")
			self._status_label.set_text("Сканирование завершено")
			self._append_log("Файлы для обработки не найдены.")
			return False

		fraction = current / total
		self._progress_bar.set_fraction(fraction)
		self._progress_bar.set_text(f"{current}/{total}")
		self._status_label.set_text(f"Сканирование файлов: {current} из {total}")
		if current == 0:
			self._append_log(f"Найдено файлов для проверки: {total}")
		elif current == total:
			self._append_log("Сканирование завершено.")
		return False

	def _finish_success(self, output_file):
		self._progress_bar.set_fraction(1.0)
		self._progress_bar.set_text("Готово")
		self._status_label.set_text(f"Файл сохранён как {output_file}")
		self._append_log(f"Файл сохранён как {output_file}")
		self._start_button.set_sensitive(True)
		return False

	def _finish_with_error(self, message):
		self._progress_bar.set_text("Ошибка")
		self._status_label.set_text("Во время обработки произошла ошибка")
		self._append_log(message)
		self._start_button.set_sensitive(True)
		return False

	def _set_log(self, message):
		self._log_buffer.set_text(message)

	def _append_log(self, message):
		end_iter = self._log_buffer.get_end_iter()
		prefix = "" if end_iter.get_offset() == 0 else "\n"
		self._log_buffer.insert(end_iter, f"{prefix}{message}")


class TranslationApplication(Gtk.Application):
	def __init__(self):
		super().__init__(application_id="club.devcraft.translation_generator")

	def do_activate(self):
		window = self.props.active_window
		if window is None:
			window = TranslationWindow(self)
		window.present()


def main():
	app = TranslationApplication()
	app.run(None)


if __name__ == "__main__":
	main()
