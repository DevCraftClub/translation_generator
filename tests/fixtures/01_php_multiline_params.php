<?php
// Multiline __() with placeholder params array
echo __(
	'Укажите путь, где будут храниться файлы базы данных.<br>По умолчанию: <code>{path}</code>',
	['{path}' => BackupPathHelper::DEFAULT_EXPORT_PATH]
);
