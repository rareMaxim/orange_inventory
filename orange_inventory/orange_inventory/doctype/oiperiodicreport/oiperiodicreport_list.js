frappe.listview_settings["oiPeriodicReport"] = {
	onload(listview) {
		// Масове створення звітів
		listview.page.add_menu_item(__("Масове створення звітів"), () => {
			show_bulk_create_dialog(listview);
		});

		// Переглянути прострочені звіти
		listview.page.add_menu_item(__("Прострочені звіти"), () => {
			show_overdue_reports(listview);
		});

		// Відправити нагадування
		listview.page.add_menu_item(__("Відправити нагадування"), () => {
			const selected = listview.get_checked_items();
			if (selected.length === 0) {
				frappe.msgprint(__("Виберіть звіти для відправки нагадувань"));
				return;
			}
			send_bulk_reminders(
				listview,
				selected.map((item) => item.name)
			);
		});
	},

	// Колірне кодування статусів
	get_indicator: function (doc) {
		const status_colors = {
			Чернетка: "grey",
			"Очікує заповнення": "orange",
			Заповнено: "blue",
			Імпортовано: "green",
			Прийнято: "green",
			Відхилено: "red",
		};

		let indicator = [
			__(doc.status),
			status_colors[doc.status] || "grey",
			"status,=," + doc.status,
		];

		// Додати індикатор для прострочених
		if (
			doc.submission_deadline &&
			new Date(doc.submission_deadline) < new Date() &&
			!["Імпортовано", "Прийнято"].includes(doc.status)
		) {
			indicator = [__("Прострочено"), "red", "status,=," + doc.status];
		}

		return indicator;
	},

	// Форматування колонок
	formatters: {
		period(value, df, doc) {
			// Додати іконку типу звіту
			const icon = doc.report_type === "Річний" ? "📅" : "📊";
			return `${icon} ${value}`;
		},
		submission_deadline(value, df, doc) {
			if (!value) return "-";

			const deadline = new Date(value);
			const today = new Date();
			const days_diff = Math.floor((deadline - today) / (1000 * 60 * 60 * 24));

			let color = "green";
			let text = value;

			if (days_diff < 0 && !["Імпортовано", "Прийнято"].includes(doc.status)) {
				color = "red";
				text = `${value} (прострочено на ${Math.abs(days_diff)} днів)`;
			} else if (days_diff >= 0 && days_diff <= 7) {
				color = "orange";
				text = `${value} (залишилось ${days_diff} днів)`;
			}

			return `<span style="color: ${color};">${text}</span>`;
		},
	},
};

function show_bulk_create_dialog(listview) {
	const d = new frappe.ui.Dialog({
		title: __("Масове створення звітів"),
		fields: [
			{
				fieldtype: "Data",
				fieldname: "period",
				label: __("Період"),
				reqd: 1,
				description: __("Формат: РРРР-Q1/Q2/Q3/Q4 (квартальний) або РРРР (річний)"),
			},
			{
				fieldtype: "Select",
				fieldname: "report_type",
				label: __("Тип звіту"),
				options: "Квартальний\nРічний",
				default: "Квартальний",
				reqd: 1,
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Date",
				fieldname: "submission_deadline",
				label: __("Термін подання"),
				description: __("Залиште порожнім для автоматичного розрахунку"),
			},
			{
				fieldtype: "Section Break",
			},
			{
				fieldtype: "MultiSelectList",
				fieldname: "organizations",
				label: __("Організації з показниками"),
				reqd: 1,
				get_data: function (txt) {
					// Отримати організації що мають показники в oiHromadaSurvey
					return frappe.call({
						method: "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.get_organizations_with_indicators",
						args: {
							txt: txt || "",
						},
						callback: function () {},
					});
				},
			},
			{
				fieldtype: "Button",
				fieldname: "select_all_orgs",
				label: __("Вибрати всі організації"),
				click: async function () {
					// Отримати всі організації
					const r = await frappe.call({
						method: "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.get_organizations_with_indicators",
						args: { txt: "" },
					});

					if (r.message && r.message.length > 0) {
						const org_values = r.message.map((org) => org.value);
						d.set_value("organizations", org_values);
						frappe.show_alert({
							message: __(`Вибрано ${org_values.length} організацій`),
							indicator: "green",
						});
					}
				},
			},
			{
				fieldtype: "Section Break",
			},
			{
				fieldtype: "HTML",
				fieldname: "info",
				options: `
					<div class="alert alert-info">
						<strong>ℹ Примітка:</strong>
						<ul>
							<li>Показано тільки організації, що мають показники в oiHromadaSurvey</li>
							<li>Звіти будуть створені зі статусом "Очікує заповнення"</li>
							<li>Якщо звіт для організації за цей період вже існує, він буде пропущений</li>
							<li>Після створення можна відправити нагадування на email</li>
						</ul>
					</div>
				`,
			},
		],
		primary_action_label: __("Створити звіти"),
		primary_action: async (values) => {
			if (!values.organizations || values.organizations.length === 0) {
				frappe.msgprint(__("Виберіть хоча б одну організацію"));
				return;
			}

			d.hide();
			frappe.show_progress(__("Створення звітів"), 0, 100, __("Обробка..."));

			try {
				const r = await frappe.call({
					method: "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.bulk_create_reports",
					args: {
						organizations: values.organizations,
						period: values.period,
						report_type: values.report_type,
						submission_deadline: values.submission_deadline || null,
					},
					freeze: true,
					freeze_message: __("Створення звітів..."),
				});

				frappe.hide_progress();

				if (r.message) {
					const result = r.message;

					let message = `
						<div style="margin-bottom: 15px;">
							<h4 style="color: #28a745;">✓ Створення завершено</h4>
							<p><strong>Створено звітів:</strong> ${result.created}</p>
							<p><strong>Пропущено (вже існують):</strong> ${result.skipped}</p>
						</div>
					`;

					if (result.errors && result.errors.length > 0) {
						message += `
							<div style="padding: 10px; background-color: #fff3cd; border-radius: 5px;">
								<h5 style="color: #856404;">⚠ Помилки:</h5>
								<ul style="margin-bottom: 0;">
						`;
						result.errors.forEach((error) => {
							message += `<li>${error}</li>`;
						});
						message += `
								</ul>
							</div>
						`;
					}

					frappe.msgprint({
						title: __("Результати створення"),
						message: message,
						indicator: "green",
						primary_action: {
							label: __("Відправити нагадування"),
							action: function () {
								if (result.report_ids && result.report_ids.length > 0) {
									send_bulk_reminders(listview, result.report_ids);
								}
							},
						},
					});

					listview.refresh();
				}
			} catch (error) {
				frappe.hide_progress();
				frappe.msgprint({
					title: __("Помилка"),
					message: error.message || __("Сталася помилка при створенні звітів"),
					indicator: "red",
				});
			}
		},
	});

	d.show();
}

function show_overdue_reports(listview) {
	const d = new frappe.ui.Dialog({
		title: __("Прострочені звіти"),
		fields: [
			{
				fieldtype: "Int",
				fieldname: "days_overdue",
				label: __("Мінімум днів прострочення"),
				default: 0,
				description: __("0 = всі прострочені"),
			},
		],
		primary_action_label: __("Показати"),
		primary_action: async (values) => {
			d.hide();

			try {
				const r = await frappe.call({
					method: "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.get_overdue_reports",
					args: {
						days_overdue: values.days_overdue || 0,
					},
				});

				if (r.message && r.message.length > 0) {
					const reports = r.message;

					let html = `
						<div style="max-height: 500px; overflow-y: auto;">
							<table class="table table-bordered table-sm">
								<thead>
									<tr>
										<th>Організація</th>
										<th>Період</th>
										<th>Статус</th>
										<th>Термін подання</th>
										<th>Файл</th>
										<th>Дії</th>
									</tr>
								</thead>
								<tbody>
					`;

					reports.forEach((report) => {
						const days_overdue = Math.floor(
							(new Date() - new Date(report.submission_deadline)) /
								(1000 * 60 * 60 * 24)
						);

						html += `
							<tr>
								<td>${report.organization_name || report.organization}</td>
								<td>${report.period}</td>
								<td>${report.status}</td>
								<td style="color: red;">${report.submission_deadline}<br>
									<small>(${days_overdue} днів тому)</small>
								</td>
								<td>${report.filled_form_attachment ? "✓" : "✗"}</td>
								<td>
									<a href="/app/oiperiodicreport/${report.name}" target="_blank">
										Відкрити
									</a>
								</td>
							</tr>
						`;
					});

					html += `
								</tbody>
							</table>
						</div>
					`;

					frappe.msgprint({
						title: __(`Знайдено прострочених звітів: ${reports.length}`),
						message: html,
						indicator: "orange",
						wide: true,
					});
				} else {
					frappe.msgprint(__("Прострочених звітів не знайдено"));
				}
			} catch (error) {
				frappe.msgprint({
					title: __("Помилка"),
					message: error.message || __("Сталася помилка"),
					indicator: "red",
				});
			}
		},
	});

	d.show();
}

function send_bulk_reminders(listview, report_ids) {
	frappe.confirm(
		__(`Відправити нагадування для ${report_ids.length} звіт(ів)?`),
		async function () {
			frappe.show_progress(__("Відправка нагадувань"), 0, 100, __("Обробка..."));

			try {
				const r = await frappe.call({
					method: "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.send_reminder_emails",
					args: {
						report_ids: report_ids,
					},
					freeze: true,
					freeze_message: __("Відправка email..."),
				});

				frappe.hide_progress();

				if (r.message) {
					const result = r.message;

					let message = `
						<div>
							<p><strong>Відправлено:</strong> ${result.sent}</p>
							<p><strong>Помилок:</strong> ${result.failed}</p>
						</div>
					`;

					if (result.errors && result.errors.length > 0) {
						message += `
							<div style="margin-top: 10px; padding: 10px; background-color: #fff3cd; border-radius: 5px;">
								<h5 style="color: #856404;">⚠ Помилки:</h5>
								<ul style="margin-bottom: 0;">
						`;
						result.errors.forEach((error) => {
							message += `<li>${error}</li>`;
						});
						message += `
								</ul>
							</div>
						`;
					}

					frappe.msgprint({
						title: __("Результати відправки"),
						message: message,
						indicator: result.sent > 0 ? "green" : "orange",
					});
				}
			} catch (error) {
				frappe.hide_progress();
				frappe.msgprint({
					title: __("Помилка"),
					message: error.message || __("Сталася помилка при відправці нагадувань"),
					indicator: "red",
				});
			}
		}
	);
}
