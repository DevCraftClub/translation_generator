function renderStatus(state, report, status) {
	if (state === 'error') {
		status.classList.add('alert');
		status.innerHTML = '<span class="mif-warning mr-1"></span><strong>' + t('Не удалось проверить ресурсы') + '</strong>'
			+ '<span class="text-small ml-2">' + (report || t('Повторите попытку позже')) + '</span>';
		status.classList.remove('d-none');
		return;
	}

	if (!report || !report.has_diff) {
		status.classList.add('success');
		status.innerHTML = '<span class="mif-checkmark mr-1"></span><strong>' + t('Все ресурсы актуальны') + '</strong>'
			+ '<span class="text-small fg-gray ml-2">' + t('На сервере: {remote}, локально: {local}', {
				remote: report ? report.remote_count : 0,
				local: report ? report.local_count : 0,
			}) + '</span>';
		status.classList.add('d-none');
		return;
	}
}

function buildUpdateDialog(data, lastUpdate) {
	const content = '<div class="dc-update-dialog">'
		+ '<p><strong>' + (data.title || t('Обновление')) + '</strong> '
		+ '<span class="badge inline bg-red fg-white">v' + (data.remote_version || data.version) + '</span></p>'
		+ '<p class="text-small fg-gray">' + t('Текущая версия: v{version}', { version: data.local_version || '—' }) + '</p>'
		+ '<p class="text-small">' + t('Обновлено: {date}', { date: lastUpdate }) + '</p>'
		+ '</div>';
	return content;
}
