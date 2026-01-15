frappe.listview_settings["oiHromadaSurvey"] = {
	onload(listview) {
		const defaultPeriod = () => {
			const now = new Date();
			const y = now.getFullYear();
			const q = Math.floor(now.getMonth() / 3); // 1..4
			return `${y}-Q${q}`;
		};

		listview.page.add_menu_item(__("Recompute Analytics for All Groups"), () => {
			frappe.call({
				method: "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.recompute_all_groups",
				args: { background: 1 },
				freeze: true,
				freeze_message: __("Recomputing analytics…"),
				callback: (r) => {
					if (r.message && r.message.status === "queued") {
						frappe.show_alert({
							message: __("Analytics recompute queued"),
							indicator: "green",
						});
					} else {
						frappe.show_alert({
							message: __("Analytics recompute started"),
							indicator: "blue",
						});
					}
				},
			});
		});
		listview.page.add_menu_item(__("Export All Templates (ZIP)"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Експорт шаблонів (ZIP)"),
				fields: [
					{
						fieldtype: "Data",
						fieldname: "period",
						label: __("Період"),
						default: defaultPeriod(),
						reqd: 1,
					},
				],
				primary_action_label: __("Згенерувати ZIP"),
				primary_action: async (values) => {
					d.hide();
					const r = await frappe.call({
						method: "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.export_all_org_templates",
						args: { period: values.period },
						freeze: true,
						freeze_message: __("Генеруємо ZIP…"),
					});
					const url = r.message && r.message.file_url;
					url
						? window.open(url, "_blank")
						: frappe.msgprint(__("Не вдалося отримати ZIP"));
				},
			});
			d.show();
		});
		listview.page.add_menu_item(__("Export Excel Template…"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Виберіть розпорядника"),
				fields: [
					{
						fieldtype: "Link",
						fieldname: "org",
						label: __("Розпорядник"),
						options: "oiOrganization",
						reqd: 1,
					},
					{
						fieldtype: "Data",
						fieldname: "period",
						label: __("Період (напр. 2025-Q3)"),
						default: defaultPeriod(),
						reqd: 1,
					},
				],
				primary_action_label: __("Згенерувати"),
				primary_action: async (values) => {
					d.hide();
					const r = await frappe.call({
						method: "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.export_org_template",
						args: values,
						freeze: true,
						freeze_message: __("Генеруємо шаблон…"),
					});
					const url = r.message && r.message.file_url;
					if (url) {
						frappe.show_alert({
							message: __("Шаблон збережено. Відкриваємо…"),
							indicator: "green",
						});
						window.open(url, "_blank");
					} else {
						frappe.msgprint(__("Не вдалося отримати посилання на файл"));
					}
				},
			});
			d.show();
		});

		// Кнопка імпорту даних з Excel
		listview.page.add_menu_item(__("Імпорт даних з Excel"), () => {
			show_import_dialog_listview(listview);
		});

		// Кнопка синхронізації з паспорта індикаторів
		listview.page.add_menu_item(__("Синхронізація з паспорта індикаторів"), () => {
			show_sync_master_dialog(listview);
		});

		// Кнопка звіту про заповнення показників
		listview.page.add_menu_item(__("Звіт про заповнення показників"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Звіт про заповнення показників"),
				fields: [
					{
						fieldtype: "Data",
						fieldname: "period",
						label: __("Період"),
						default: defaultPeriod(),
						reqd: 1,
						description: __("Період для звіту (напр. 2025-Q1)"),
					},
					{
						fieldtype: "Section Break",
					},
					{
						fieldtype: "HTML",
						fieldname: "info",
						options: `
							<div style="padding: 10px; background-color: #e3f2fd; border-radius: 5px; margin-bottom: 10px;">
								<h4 style="margin-top: 0;">📊 Що включає звіт:</h4>
								<ul style="margin-bottom: 0;">
									<li>Статус заповнення для кожної організації</li>
									<li>Кількість заповнених та незаповнених показників</li>
									<li>Дата останнього оновлення та хто змінив</li>
									<li>Детальний список незаповнених показників</li>
									<li>Процент виконання по кожній організації</li>
								</ul>
							</div>
						`,
					},
				],
				primary_action_label: __("Згенерувати звіт"),
				primary_action: async (values) => {
					d.hide();
					frappe.show_progress(__("Генерація звіту"), 50, 100, __("Обробка даних..."));

					try {
						const r = await frappe.call({
							method: "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.generate_completion_report",
							args: { period: values.period },
							freeze: true,
							freeze_message: __("Генеруємо звіт про заповнення…"),
						});

						frappe.hide_progress();

						if (r.message && r.message.file_url) {
							const result = r.message;
							frappe.show_alert({
								message: __(
									`Звіт готовий! Всього організацій: ${result.total_orgs}, Заповнили: ${result.filled_orgs}, Не заповнили: ${result.unfilled_orgs}`
								),
								indicator: "green",
							});
							window.open(result.file_url, "_blank");
						} else {
							frappe.msgprint(__("Не вдалося згенерувати звіт"));
						}
					} catch (error) {
						frappe.hide_progress();
						frappe.msgprint({
							title: __("Помилка"),
							message: error.message || __("Сталася помилка при генерації звіту"),
							indicator: "red",
						});
					}
				},
			});
			d.show();
		});
	},
};

function show_import_dialog_listview(listview) {
	let d = new frappe.ui.Dialog({
		title: __("Імпорт даних з Excel"),
		fields: [
			{
				label: __("Виберіть файл Excel"),
				fieldname: "import_file",
				fieldtype: "Attach",
				reqd: 1,
				options: {
					restrictions: {
						allowed_file_types: [".xlsx", ".xls"],
					},
				},
			},
			{
				fieldname: "column_break",
				fieldtype: "Column Break",
			},
			{
				label: __("Організація (опціонально)"),
				fieldname: "organization",
				fieldtype: "Link",
				options: "oiOrganization",
				description: __("Залиште порожнім для імпорту всіх організацій з файлу"),
			},
			{
				fieldname: "section_break",
				fieldtype: "Section Break",
			},
			{
				label: __("Інструкції"),
				fieldname: "instructions",
				fieldtype: "HTML",
				options: `
					<div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
						<h4>Як використовувати:</h4>
						<ol>
							<li>Завантажте файл Excel, згенерований через "Export Excel Template"</li>
							<li>Відредагуйте значення в колонці <strong>G</strong> (Значення для заповнення)</li>
							<li>Завантажте файл та натисніть "Імпортувати"</li>
						</ol>
						<p><strong>Примітка:</strong> Система автоматично знайде показники за ID (колонка B).
						Оновлюються тільки записи з новими значеннями. Поля only_admin пропускаються.</p>
					</div>
				`,
			},
		],
		primary_action_label: __("Імпортувати"),
		primary_action: function (values) {
			if (!values.import_file) {
				frappe.msgprint(__("Будь ласка, виберіть файл"));
				return;
			}

			// Показуємо індикатор завантаження
			frappe.show_progress(__("Імпорт даних"), 0, 100, __("Обробка файлу..."));

			frappe.call({
				method: "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.import_from_excel",
				args: {
					file_url: values.import_file,
					org: values.organization || null,
				},
				callback: function (r) {
					frappe.hide_progress();

					if (r.message && r.message.status === "success") {
						const result = r.message;

						// Формуємо повідомлення про результати
						let message = `
							<div style="margin-bottom: 15px;">
								<h4 style="color: #28a745;">✓ Імпорт завершено успішно</h4>
								<p><strong>Оновлено записів:</strong> ${result.updated}</p>
								<p><strong>Пропущено записів:</strong> ${result.skipped}</p>
							</div>
						`;

						// Додаємо детальну інформацію про зміни
						if (result.details && result.details.length > 0) {
							message += `
								<div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 5px;">
									<h5>Змінені значення:</h5>
									<table class="table table-sm">
										<thead>
											<tr>
												<th>ID</th>
												<th>Назва</th>
												<th>Старе значення</th>
												<th>Нове значення</th>
											</tr>
										</thead>
										<tbody>
							`;

							result.details.forEach(function (detail) {
								message += `
									<tr>
										<td><code>${detail.id}</code></td>
										<td>${detail.title}</td>
										<td>${detail.old_value}</td>
										<td><strong>${detail.new_value}</strong></td>
									</tr>
								`;
							});

							message += `
										</tbody>
									</table>
								</div>
							`;
						}

						// Додаємо помилки якщо є
						if (result.errors && result.errors.length > 0) {
							message += `
								<div style="margin-top: 15px; padding: 10px; background-color: #fff3cd; border-radius: 5px;">
									<h5 style="color: #856404;">⚠ Помилки при імпорті:</h5>
									<ul style="margin-bottom: 0;">
							`;

							result.errors.forEach(function (error) {
								message += `<li>${error}</li>`;
							});

							message += `
									</ul>
								</div>
							`;
						}

						frappe.msgprint({
							title: __("Результати імпорту"),
							message: message,
							indicator: "green",
							primary_action: {
								label: __("Оновити список"),
								action: function () {
									listview.refresh();
								},
							},
						});

						d.hide();
					} else {
						frappe.msgprint({
							title: __("Помилка імпорту"),
							message: r.message
								? r.message.errors.join("<br>")
								: __("Невідома помилка"),
							indicator: "red",
						});
					}
				},
				error: function (r) {
					frappe.hide_progress();
					frappe.msgprint({
						title: __("Помилка"),
						message: r.message || __("Сталася помилка при імпорті даних"),
						indicator: "red",
					});
				},
			});
		},
	});

	d.show();
}

/**
 * Діалог синхронізації структури показників з Excel файлу паспорта індикаторів.
 * Цей імпорт оновлює структуру (групи, підгрупи, індикатори, показники),
 * а не значення даних.
 */
function show_sync_master_dialog(listview) {
	let d = new frappe.ui.Dialog({
		title: __("Синхронізація з паспорта індикаторів"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "info",
				options: `
					<div style="padding: 15px; background-color: #e8f4fd; border-radius: 8px; margin-bottom: 15px;">
						<h4 style="margin-top: 0; color: #1565c0;">📋 Синхронізація структури індикаторів</h4>
						<p>Цей інструмент синхронізує структуру показників з офіційного Excel файлу
						"Індекс територіальних громад" (Паспорт індикаторів).</p>
						<h5>Що буде синхронізовано:</h5>
						<ul style="margin-bottom: 0;">
							<li><strong>Групи верхнього рівня</strong> (A, B, C, D)</li>
							<li><strong>Підгрупи</strong> (A.1, A.2, B.1 тощо)</li>
							<li><strong>Індикатори</strong> (A.1.1, A.1.2 тощо)</li>
							<li><strong>Показники</strong> (A.1.1.1, A.1.1.2 тощо)</li>
						</ul>
					</div>
					<div style="padding: 10px; background-color: #fff3cd; border-radius: 5px; margin-bottom: 15px;">
						<strong>⚠️ Увага:</strong>
						<ul style="margin-bottom: 0;">
							<li>Нові записи будуть <strong>створені</strong></li>
							<li>Існуючі записи будуть <strong>оновлені</strong> (назви, описи, періодичність)</li>
							<li>Записи <strong>НЕ видаляються</strong></li>
							<li>Значення даних (int_data, bool_data) <strong>НЕ змінюються</strong></li>
						</ul>
					</div>
				`,
			},
			{
				label: __("Файл паспорта індикаторів"),
				fieldname: "master_file",
				fieldtype: "Attach",
				reqd: 1,
				description: __("Завантажте Excel файл 'Індекс територіальних громад'"),
				options: {
					restrictions: {
						allowed_file_types: [".xlsx", ".xls"],
					},
				},
			},
			{
				fieldtype: "Section Break",
				label: __("Режим виконання"),
			},
			{
				label: __("Тільки перегляд (без змін)"),
				fieldname: "dry_run",
				fieldtype: "Check",
				default: 1,
				description: __("Спочатку рекомендуємо запустити в режимі перегляду"),
			},
		],
		size: "large",
		primary_action_label: __("Аналізувати"),
		primary_action: function (values) {
			if (!values.master_file) {
				frappe.msgprint(__("Будь ласка, виберіть файл"));
				return;
			}

			const method_name = values.dry_run
				? "orange_inventory.orange_inventory.doctype.oihromadasurvey.sync_master_excel.get_sync_preview"
				: "orange_inventory.orange_inventory.doctype.oihromadasurvey.sync_master_excel.sync_from_master_excel";

			const action_label = values.dry_run ? "Аналіз" : "Синхронізація";

			frappe.show_progress(__(`${action_label}...`), 30, 100, __("Обробка файлу..."));

			frappe.call({
				method: method_name,
				args: {
					file_url: values.master_file,
					dry_run: values.dry_run ? 1 : 0,
				},
				callback: function (r) {
					frappe.hide_progress();

					if (r.message) {
						const result = r.message;
						show_sync_results_dialog(result, values.dry_run, listview, d);
					} else {
						frappe.msgprint({
							title: __("Помилка"),
							message: __("Не вдалося обробити файл"),
							indicator: "red",
						});
					}
				},
				error: function (r) {
					frappe.hide_progress();
					frappe.msgprint({
						title: __("Помилка"),
						message: r.message || __("Сталася помилка при обробці файлу"),
						indicator: "red",
					});
				},
			});
		},
	});

	d.show();
}

/**
 * Показує результати синхронізації
 */
function show_sync_results_dialog(result, isDryRun, listview, parentDialog) {
	const statusIcon = result.status === "success" ? "✓" : "⚠";
	const modeLabel = isDryRun ? "ПОПЕРЕДНІЙ ПЕРЕГЛЯД" : "СИНХРОНІЗАЦІЯ ЗАВЕРШЕНА";

	let message = `
		<div style="margin-bottom: 20px;">
			<div style="padding: 15px; background-color: ${
				isDryRun ? "#e3f2fd" : "#e8f5e9"
			}; border-radius: 8px; margin-bottom: 15px;">
				<h4 style="margin: 0; color: ${isDryRun ? "#1565c0" : "#2e7d32"};">
					${statusIcon} ${modeLabel}
				</h4>
			</div>

			<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 15px;">
				<div style="padding: 15px; background: #f5f5f5; border-radius: 8px; text-align: center;">
					<div style="font-size: 24px; font-weight: bold; color: #1976d2;">${result.total_in_file || 0}</div>
					<div style="font-size: 12px; color: #666;">У файлі</div>
				</div>
				<div style="padding: 15px; background: #e8f5e9; border-radius: 8px; text-align: center;">
					<div style="font-size: 24px; font-weight: bold; color: #2e7d32;">${result.created || 0}</div>
					<div style="font-size: 12px; color: #666;">Створено</div>
				</div>
				<div style="padding: 15px; background: #fff3e0; border-radius: 8px; text-align: center;">
					<div style="font-size: 24px; font-weight: bold; color: #f57c00;">${result.updated || 0}</div>
					<div style="font-size: 12px; color: #666;">Оновлено</div>
				</div>
				<div style="padding: 15px; background: #f5f5f5; border-radius: 8px; text-align: center;">
					<div style="font-size: 24px; font-weight: bold; color: #757575;">${result.unchanged || 0}</div>
					<div style="font-size: 12px; color: #666;">Без змін</div>
				</div>
			</div>
	`;

	// Деталі змін
	if (result.details && result.details.length > 0) {
		message += `
			<div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 15px;">
				<table class="table table-sm" style="margin-bottom: 0;">
					<thead style="position: sticky; top: 0; background: #f5f5f5;">
						<tr>
							<th style="width: 80px;">Дія</th>
							<th style="width: 100px;">ID</th>
							<th>Назва</th>
							<th>Деталі</th>
						</tr>
					</thead>
					<tbody>
		`;

		result.details.forEach(function (detail) {
			const actionColor = detail.action === "created" ? "#2e7d32" : "#f57c00";
			const actionLabel = detail.action === "created" ? "Створено" : "Оновлено";
			const changes = detail.changes ? detail.changes.join(", ") : detail.parent || "-";

			message += `
				<tr>
					<td><span style="color: ${actionColor}; font-weight: bold;">${actionLabel}</span></td>
					<td><code>${detail.id}</code></td>
					<td>${detail.title}</td>
					<td style="font-size: 11px; color: #666;">${changes}</td>
				</tr>
			`;
		});

		message += `
					</tbody>
				</table>
			</div>
		`;

		if (result.details.length >= 100) {
			message += `
				<div style="padding: 10px; background: #fff3cd; border-radius: 5px; margin-bottom: 15px; text-align: center;">
					<small>Показано перші 100 записів</small>
				</div>
			`;
		}
	}

	// Помилки
	if (result.errors && result.errors.length > 0) {
		message += `
			<div style="padding: 15px; background-color: #ffebee; border-radius: 8px; margin-bottom: 15px;">
				<h5 style="color: #c62828; margin-top: 0;">⚠ Помилки (${result.errors.length}):</h5>
				<ul style="margin-bottom: 0; max-height: 150px; overflow-y: auto;">
		`;

		result.errors.forEach(function (error) {
			message += `<li style="color: #c62828;">${error}</li>`;
		});

		message += `
				</ul>
			</div>
		`;
	}

	message += `</div>`;

	// Показуємо діалог з результатами
	const resultDialog = new frappe.ui.Dialog({
		title: __("Результати синхронізації"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "result_html",
				options: message,
			},
		],
		primary_action_label: isDryRun ? __("Виконати синхронізацію") : __("Закрити"),
		primary_action: function () {
			if (isDryRun && (result.created > 0 || result.updated > 0)) {
				// Запускаємо реальну синхронізацію
				resultDialog.hide();
				parentDialog.set_value("dry_run", 0);
				parentDialog.$primary_btn.trigger("click");
			} else {
				resultDialog.hide();
				parentDialog.hide();
				if (!isDryRun) {
					listview.refresh();
				}
			}
		},
		secondary_action_label: isDryRun ? __("Закрити") : null,
		secondary_action: function () {
			resultDialog.hide();
		},
	});

	resultDialog.show();
}
