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
