// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiHromadaSettings", {
	refresh(frm) {
		frm.disable_save();
		frm.page.set_primary_action(__("Зберегти"), () => {
			frm.save();
		});

		// Оновити статус при завантаженні
		frm.trigger("update_status_html");
	},

	fetch_parameters_btn(frm) {
		frappe.confirm(__("Отримати актуальні параметри з порталу hromada.gov.ua?"), () => {
			frappe.call({
				method: "orange_inventory.orange_inventory.doctype.oihromadasettings.hromada_sync.fetch_portal_parameters",
				freeze: true,
				freeze_message: __("Отримання параметрів..."),
				callback: function (r) {
					if (r.message) {
						if (r.message.status === "success") {
							// Дані про зміни статусів вже включені в відповідь
							const data = r.message;

							if (data.no_status_changes) {
								// Немає змін статусів - просто показуємо результат
								frappe.msgprint({
									title: __("Успішно"),
									message: __(
										"Отримано {0} параметрів з порталу. Замаплено: {1}",
										[data.total, data.mapped]
									),
									indicator: "green",
								});
								frm.reload_doc();
							} else {
								// Є зміни статусів - показуємо діалог
								show_enabled_status_dialog(frm, data, {
									to_disable: data.to_disable,
									to_enable: data.to_enable,
								});
							}
						} else {
							frappe.msgprint({
								title: __("Помилка"),
								message: r.message.error || __("Невідома помилка"),
								indicator: "red",
							});
						}
					}
				},
			});
		});
	},

	sync_to_portal_btn(frm) {
		// Спочатку отримуємо порівняння локальних та портальних значень
		frappe.call({
			method: "orange_inventory.orange_inventory.doctype.oihromadasettings.hromada_sync.get_sync_comparison",
			freeze: true,
			freeze_message: __("Завантаження даних з порталу..."),
			callback: function (r) {
				if (r.message) {
					if (r.message.status === "error") {
						frappe.msgprint({
							title: __("Помилка"),
							message: r.message.error || __("Невідома помилка"),
							indicator: "red",
						});
						return;
					}

					const data = r.message;
					if (data.total === 0) {
						frappe.msgprint({
							title: __("Немає даних"),
							message: __(
								"Немає показників для синхронізації. Спочатку виконайте mapping."
							),
							indicator: "orange",
						});
						return;
					}

					// Показуємо діалог з порівнянням
					show_sync_comparison_dialog(frm, data);
				}
			},
		});
	},

	auto_map_btn(frm) {
		frappe.call({
			method: "orange_inventory.orange_inventory.doctype.oihromadasettings.hromada_sync.auto_map_parameters",
			freeze: true,
			freeze_message: __("Виконання mapping..."),
			callback: function (r) {
				if (r.message) {
					frappe.msgprint({
						title: __("Mapping завершено"),
						message: __("Створено: {0}, Оновлено: {1}, Без змін: {2}", [
							r.message.created,
							r.message.updated,
							r.message.unchanged,
						]),
						indicator: "green",
					});
					frm.reload_doc();
				}
			},
		});
	},

	view_mapping_btn() {
		frappe.set_route("List", "oiHromadaSurvey", {
			hromada_parameter_id: ["is", "set"],
		});
	},

	update_status_html(frm) {
		let html = "";
		if (frm.doc.last_sync_date) {
			html += `<div class="alert alert-info">
				<strong>Остання синхронізація:</strong> ${frappe.datetime.str_to_user(frm.doc.last_sync_date)}
			</div>`;
		}
		if (frm.doc.community_id) {
			html += `<div class="alert alert-success">
				<strong>Community ID:</strong> ${frm.doc.community_id}
			</div>`;
		} else {
			html += `<div class="alert alert-warning">
				<strong>Увага:</strong> Натисніть "Отримати параметри з порталу" для початку роботи.
			</div>`;
		}
		frm.set_df_property("sync_status_html", "options", html);
	},
});

/**
 * Показати діалог з порівнянням локальних та портальних значень
 */
function show_sync_comparison_dialog(frm, data) {
	// Генеруємо HTML таблиці
	let table_html = `
		<div class="sync-comparison-summary" style="margin-bottom: 15px;">
			<span class="badge badge-primary" style="margin-right: 10px;">
				Всього: ${data.total}
			</span>
			<span class="badge badge-warning" style="margin-right: 10px;">
				Змінено: ${data.changed}
			</span>
			<span class="badge badge-success">
				Без змін: ${data.unchanged}
			</span>
		</div>
		<div style="max-height: 400px; overflow-y: auto;">
		<table class="table table-bordered table-sm" style="font-size: 12px;">
			<thead class="thead-light">
				<tr>
					<th style="width: 30px;">
						<input type="checkbox" id="select-all-params" checked>
					</th>
					<th>Код</th>
					<th>Назва</th>
					<th style="text-align: center;">Локальне</th>
					<th style="text-align: center;">На порталі</th>
					<th style="text-align: center;">Статус</th>
				</tr>
			</thead>
			<tbody>
	`;

	data.comparison.forEach((item) => {
		const row_class = item.is_changed ? "table-warning" : "";
		const status_badge = item.is_changed
			? '<span class="badge badge-warning">Змінено</span>'
			: '<span class="badge badge-success">Однаково</span>';

		// Показуємо різницю кольором
		const local_style = item.is_changed ? "font-weight: bold; color: #28a745;" : "";
		const portal_style = item.is_changed ? "color: #6c757d;" : "";

		table_html += `
			<tr class="${row_class}">
				<td style="text-align: center;">
					<input type="checkbox" class="param-checkbox"
						data-param-id="${item.parameter_id}"
						${item.is_changed ? "checked" : ""}>
				</td>
				<td><code>${item.parameter_code || item.survey_id}</code></td>
				<td title="${item.title}">${
			item.title.length > 50 ? item.title.substring(0, 50) + "..." : item.title
		}</td>
				<td style="text-align: center; ${local_style}">${item.local_display}</td>
				<td style="text-align: center; ${portal_style}">${item.portal_display}</td>
				<td style="text-align: center;">${status_badge}</td>
			</tr>
		`;
	});

	table_html += `
			</tbody>
		</table>
		</div>
	`;

	// Створюємо діалог
	const dialog = new frappe.ui.Dialog({
		title: __("Порівняння значень з порталом hromada.gov.ua"),
		size: "extra-large",
		fields: [
			{
				fieldname: "comparison_html",
				fieldtype: "HTML",
				options: table_html,
			},
		],
		primary_action_label: __("Відправити обрані на портал"),
		primary_action: function () {
			// Збираємо обрані параметри
			const selected_ids = [];
			dialog.$wrapper.find(".param-checkbox:checked").each(function () {
				selected_ids.push($(this).data("param-id"));
			});

			if (selected_ids.length === 0) {
				frappe.msgprint({
					title: __("Увага"),
					message: __("Оберіть хоча б один параметр для синхронізації"),
					indicator: "orange",
				});
				return;
			}

			dialog.hide();

			// Відправляємо обрані параметри
			frappe.call({
				method: "orange_inventory.orange_inventory.doctype.oihromadasettings.hromada_sync.sync_selected_to_portal",
				args: {
					parameter_ids: JSON.stringify(selected_ids),
				},
				freeze: true,
				freeze_message: __("Відправка даних на портал..."),
				callback: function (r) {
					if (r.message) {
						if (r.message.status === "success") {
							frappe.msgprint({
								title: __("Успішно"),
								message: __("Відправлено {0} параметрів на портал.", [
									r.message.updated,
								]),
								indicator: "green",
							});
							frm.reload_doc();
						} else {
							frappe.msgprint({
								title: __("Помилка"),
								message: r.message.error || __("Невідома помилка"),
								indicator: "red",
							});
						}
					}
				},
			});
		},
		secondary_action_label: __("Скасувати"),
	});

	dialog.show();

	// Обробник "Вибрати все"
	dialog.$wrapper.find("#select-all-params").on("change", function () {
		const is_checked = $(this).prop("checked");
		dialog.$wrapper.find(".param-checkbox").prop("checked", is_checked);
	});

	// Оновлюємо "Вибрати все" при зміні окремих чекбоксів
	dialog.$wrapper.find(".param-checkbox").on("change", function () {
		const total = dialog.$wrapper.find(".param-checkbox").length;
		const checked = dialog.$wrapper.find(".param-checkbox:checked").length;
		dialog.$wrapper.find("#select-all-params").prop("checked", total === checked);
	});
}

/**
 * Показати діалог зі змінами статусів enabled
 */
function show_enabled_status_dialog(frm, fetch_result, status_data) {
	let html = `
		<div class="alert alert-info">
			<strong>Отримано ${fetch_result.total} параметрів з порталу. Замаплено: ${fetch_result.mapped}</strong>
		</div>
	`;

	// Таблиця показників для вимкнення
	if (status_data.to_disable && status_data.to_disable.length > 0) {
		html += `
			<h5 style="color: #dc3545; margin-top: 15px;">
				<i class="fa fa-minus-circle"></i> Буде вимкнено (${status_data.to_disable.length}):
			</h5>
			<p class="text-muted small">Ці показники присутні локально, але відсутні на порталі</p>
			<div style="max-height: 200px; overflow-y: auto;">
			<table class="table table-sm table-bordered" style="font-size: 12px;">
				<thead class="thead-light">
					<tr>
						<th style="width: 30px;"><input type="checkbox" id="select-all-disable" checked></th>
						<th>Код</th>
						<th>Назва</th>
					</tr>
				</thead>
				<tbody>
		`;

		status_data.to_disable.forEach((item) => {
			html += `
				<tr class="table-danger">
					<td style="text-align: center;">
						<input type="checkbox" class="disable-checkbox" data-name="${item.name}" checked>
					</td>
					<td><code>${item.parameter_code || item.id}</code></td>
					<td title="${item.title}">${
				item.title.length > 60 ? item.title.substring(0, 60) + "..." : item.title
			}</td>
				</tr>
			`;
		});

		html += `
				</tbody>
			</table>
			</div>
		`;
	}

	// Таблиця показників для увімкнення
	if (status_data.to_enable && status_data.to_enable.length > 0) {
		html += `
			<h5 style="color: #28a745; margin-top: 15px;">
				<i class="fa fa-plus-circle"></i> Буде увімкнено (${status_data.to_enable.length}):
			</h5>
			<p class="text-muted small">Ці показники вимкнені локально, але присутні на порталі</p>
			<div style="max-height: 200px; overflow-y: auto;">
			<table class="table table-sm table-bordered" style="font-size: 12px;">
				<thead class="thead-light">
					<tr>
						<th style="width: 30px;"><input type="checkbox" id="select-all-enable" checked></th>
						<th>Код</th>
						<th>Назва</th>
					</tr>
				</thead>
				<tbody>
		`;

		status_data.to_enable.forEach((item) => {
			html += `
				<tr class="table-success">
					<td style="text-align: center;">
						<input type="checkbox" class="enable-checkbox" data-name="${item.name}" checked>
					</td>
					<td><code>${item.parameter_code || item.id}</code></td>
					<td title="${item.title}">${
				item.title.length > 60 ? item.title.substring(0, 60) + "..." : item.title
			}</td>
				</tr>
			`;
		});

		html += `
				</tbody>
			</table>
			</div>
		`;
	}

	// Створюємо діалог
	const dialog = new frappe.ui.Dialog({
		title: __("Зміни статусів показників"),
		size: "large",
		fields: [
			{
				fieldname: "status_html",
				fieldtype: "HTML",
				options: html,
			},
		],
		primary_action_label: __("Застосувати зміни"),
		primary_action: function () {
			// Збираємо обрані показники
			const to_disable = [];
			const to_enable = [];

			dialog.$wrapper.find(".disable-checkbox:checked").each(function () {
				to_disable.push($(this).data("name"));
			});

			dialog.$wrapper.find(".enable-checkbox:checked").each(function () {
				to_enable.push($(this).data("name"));
			});

			if (to_disable.length === 0 && to_enable.length === 0) {
				dialog.hide();
				frm.reload_doc();
				return;
			}

			dialog.hide();

			// Застосовуємо зміни
			frappe.call({
				method: "orange_inventory.orange_inventory.doctype.oihromadasettings.hromada_sync.apply_enabled_status_changes",
				args: {
					to_disable: JSON.stringify(to_disable),
					to_enable: JSON.stringify(to_enable),
				},
				freeze: true,
				freeze_message: __("Застосування змін..."),
				callback: function (r) {
					if (r.message && r.message.status === "success") {
						frappe.msgprint({
							title: __("Успішно"),
							message: __("Вимкнено: {0}, Увімкнено: {1}", [
								r.message.disabled,
								r.message.enabled,
							]),
							indicator: "green",
						});
					}
					frm.reload_doc();
				},
			});
		},
		secondary_action_label: __("Пропустити"),
		secondary_action: function () {
			dialog.hide();
			frm.reload_doc();
		},
	});

	dialog.show();

	// Обробники "Вибрати все"
	dialog.$wrapper.find("#select-all-disable").on("change", function () {
		dialog.$wrapper.find(".disable-checkbox").prop("checked", $(this).prop("checked"));
	});

	dialog.$wrapper.find("#select-all-enable").on("change", function () {
		dialog.$wrapper.find(".enable-checkbox").prop("checked", $(this).prop("checked"));
	});
}
