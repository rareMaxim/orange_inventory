// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiPeriodicReport", {
	refresh: function (frm) {
		// Додати кнопки залежно від статусу
		add_custom_buttons(frm);

		// Оновити HTML інструкції
		update_template_instructions(frm);

		// Підсвітити прострочені звіти
		highlight_overdue(frm);
	},

	report_type: function (frm) {
		// Підказка для формату періоду
		if (frm.doc.report_type === "Квартальний") {
			frappe.msgprint({
				title: __("Формат періоду"),
				message: __("Введіть період у форматі РРРР-Q1/Q2/Q3/Q4 (наприклад, 2025-Q1)"),
				indicator: "blue",
			});
		} else if (frm.doc.report_type === "Річний") {
			frappe.msgprint({
				title: __("Формат періоду"),
				message: __("Введіть період у форматі РРРР (наприклад, 2025)"),
				indicator: "blue",
			});
		}
	},

	period: function (frm) {
		// Автоматично визначити термін подання
		auto_set_submission_deadline(frm);
	},

	filled_form_attachment: function (frm) {
		// Автоматично встановити дату прикріплення відображається в before_save
		if (frm.doc.filled_form_attachment && frm.doc.status === "Очікує заповнення") {
			frappe.show_alert({
				message: __("Файл прикріплено. Статус змінено на 'Заповнено'"),
				indicator: "green",
			});
		}
	},
});

function add_custom_buttons(frm) {
	// Очистити попередні кнопки
	frm.clear_custom_buttons();

	// Кнопка "Завантажити шаблон"
	if (frm.doc.organization && frm.doc.period) {
		frm.add_custom_button(
			__("Завантажити шаблон Excel"),
			function () {
				download_template(frm);
			},
			__("Дії")
		);
	}

	// Кнопка "Імпортувати дані" - тільки якщо є прикріплений файл
	if (
		frm.doc.filled_form_attachment &&
		["Заповнено", "Помилка"].includes(frm.doc.import_status || frm.doc.status)
	) {
		frm.add_custom_button(
			__("Імпортувати дані"),
			function () {
				import_from_attachment(frm, false);
			},
			__("Дії")
		);
	}

	// Кнопка "Ре-імпорт" - якщо вже імпортовано але є новий файл
	if (
		frm.doc.filled_form_attachment &&
		frm.doc.import_status === "Успішно" &&
		frm.doc.status === "Імпортовано"
	) {
		frm.add_custom_button(
			__("Ре-імпорт даних"),
			function () {
				reimport_data(frm);
			},
			__("Дії")
		);
	}

	// Кнопка "Відправити нагадування" - для адміністраторів
	if (
		frappe.user.has_role("System Manager") &&
		["Очікує заповнення", "Заповнено"].includes(frm.doc.status)
	) {
		frm.add_custom_button(
			__("Відправити нагадування"),
			function () {
				send_reminder(frm);
			},
			__("Дії")
		);
	}

	// Кнопка "Переглянути зміни" - після імпорту
	if (frm.doc.import_status === "Успішно" && frm.doc.import_details) {
		frm.add_custom_button(
			__("Переглянути деталі імпорту"),
			function () {
				show_import_details(frm);
			},
			__("Дії")
		);
	}
}

function download_template(frm) {
	frappe.show_progress(__("Генерація шаблону"), 50, 100, __("Генеруємо Excel файл..."));

	frappe.call({
		method: "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.download_template",
		args: {
			report_id: frm.doc.name,
		},
		freeze: true,
		freeze_message: __("Завантаження шаблону..."),
		callback: function (r) {
			frappe.hide_progress();

			if (r.message && r.message.file_url) {
				frappe.show_alert({
					message: __("Шаблон готовий! Відкриваємо файл..."),
					indicator: "green",
				});
				window.open(r.message.file_url, "_blank");

				// Оновити статус якщо потрібно
				if (frm.doc.status === "Чернетка") {
					frm.set_value("status", "Очікує заповнення");
					frm.save();
				}
			} else {
				frappe.msgprint(__("Не вдалося згенерувати шаблон"));
			}
		},
		error: function (r) {
			frappe.hide_progress();
			frappe.msgprint({
				title: __("Помилка"),
				message: r.message || __("Сталася помилка при генерації шаблону"),
				indicator: "red",
			});
		},
	});
}

function import_from_attachment(frm, force_reimport = false) {
	const confirm_msg = force_reimport
		? __(
				"Ви впевнені що хочете виконати ре-імпорт?<br><br><strong>⚠ Це замінить попередньо імпортовані дані!</strong><br>Історія попереднього імпорту буде збережена в коментарях."
		  )
		: __("Імпортувати дані з прикріпленого файлу?<br><br>Це оновить показники в системі.");

	frappe.confirm(confirm_msg, function () {
		frappe.show_progress(__("Імпорт даних"), 0, 100, __("Обробка файлу..."));

		frappe.call({
			method: "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.import_from_attachment",
			args: {
				report_id: frm.doc.name,
				force_reimport: force_reimport ? 1 : 0,
			},
			freeze: true,
			freeze_message: __("Імпорт даних..."),
			callback: function (r) {
				frappe.hide_progress();

				if (r.message && r.message.status === "success") {
					const result = r.message;

					frappe.show_alert({
						message: __(
							`Імпорт завершено! Оновлено: ${result.updated}, Пропущено: ${result.skipped}`
						),
						indicator: "green",
					});

					// Показати детальні результати
					let details_html = `
							<div style="margin-bottom: 15px;">
								<h4 style="color: #28a745;">✓ Імпорт завершено успішно</h4>
								<p><strong>Оновлено записів:</strong> ${result.updated}</p>
								<p><strong>Пропущено записів:</strong> ${result.skipped}</p>
							</div>
						`;

					if (result.details && result.details.length > 0) {
						details_html += `
								<div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 5px;">
									<h5>Змінені значення:</h5>
									<table class="table table-sm table-bordered">
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
							details_html += `
									<tr>
										<td><code>${detail.id}</code></td>
										<td>${detail.title}</td>
										<td>${detail.old_value}</td>
										<td><strong>${detail.new_value}</strong></td>
									</tr>
								`;
						});

						details_html += `
										</tbody>
									</table>
								</div>
							`;
					}

					if (result.errors && result.errors.length > 0) {
						details_html += `
								<div style="margin-top: 15px; padding: 10px; background-color: #fff3cd; border-radius: 5px;">
									<h5 style="color: #856404;">⚠ Попередження:</h5>
									<ul style="margin-bottom: 0;">
							`;

						result.errors.forEach(function (error) {
							details_html += `<li>${error}</li>`;
						});

						details_html += `
									</ul>
								</div>
							`;
					}

					frappe.msgprint({
						title: __("Результати імпорту"),
						message: details_html,
						indicator: "green",
					});

					// Оновити форму
					frm.reload_doc();
				} else {
					frappe.msgprint({
						title: __("Помилка імпорту"),
						message: r.message
							? r.message.errors.join("<br>")
							: __("Невідома помилка"),
						indicator: "red",
					});
					frm.reload_doc();
				}
			},
			error: function (r) {
				frappe.hide_progress();
				frappe.msgprint({
					title: __("Помилка"),
					message: r.message || __("Сталася помилка при імпорті даних"),
					indicator: "red",
				});
				frm.reload_doc();
			},
		});
	});
}

function reimport_data(frm) {
	// Показати діалог з поясненням
	const d = new frappe.ui.Dialog({
		title: __("Ре-імпорт даних"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "warning",
				options: `
					<div class="alert alert-warning">
						<h4>⚠ Важливо!</h4>
						<p>Ре-імпорт замінить попередньо імпортовані дані новими значеннями з прикріпленого файлу.</p>
						<h5>Що станеться:</h5>
						<ul>
							<li>✓ Історія попереднього імпорту буде збережена в коментарях</li>
							<li>✓ Дані в oiHromadaSurvey будуть оновлені</li>
							<li>✓ Створюється новий запис в історії змін (oiHromadaSurveyHistory)</li>
						</ul>
						<h5>Коли використовувати:</h5>
						<ul>
							<li>Знайдено помилки в даних після імпорту</li>
							<li>Потрібно внести корективи в показники</li>
							<li>Отримано оновлені дані від розпорядника</li>
						</ul>
					</div>
				`,
			},
			{
				fieldtype: "Section Break",
			},
			{
				fieldtype: "Check",
				fieldname: "confirm_reimport",
				label: __("Я розумію що попередні дані будуть замінені"),
				reqd: 1,
			},
		],
		primary_action_label: __("Виконати ре-імпорт"),
		primary_action: (values) => {
			if (!values.confirm_reimport) {
				frappe.msgprint(__("Підтвердіть що розумієте наслідки"));
				return;
			}
			d.hide();
			import_from_attachment(frm, true);
		},
	});

	d.show();
}

function send_reminder(frm) {
	frappe.confirm(__("Відправити нагадування на email організації?"), function () {
		frappe.call({
			method: "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.send_reminder_emails",
			args: {
				report_ids: [frm.doc.name],
			},
			callback: function (r) {
				if (r.message && r.message.sent > 0) {
					frappe.show_alert({
						message: __("Нагадування відправлено"),
						indicator: "green",
					});
				} else if (r.message && r.message.errors.length > 0) {
					frappe.msgprint({
						title: __("Помилка"),
						message: r.message.errors.join("<br>"),
						indicator: "red",
					});
				}
			},
		});
	});
}

function show_import_details(frm) {
	const details = frm.doc.import_details || "Немає деталей";

	frappe.msgprint({
		title: __("Деталі імпорту"),
		message: `<pre style="white-space: pre-wrap; font-family: monospace;">${details}</pre>`,
		indicator: "blue",
	});
}

function update_template_instructions(frm) {
	// Динамічно оновити HTML інструкції
	if (frm.fields_dict.download_template_html && frm.doc.organization && frm.doc.period) {
		const html = `
			<div class="alert alert-info" style="margin-bottom: 20px;">
				<strong>📋 Інструкції для заповнення звіту:</strong>
				<ol style="margin-top: 10px; margin-bottom: 10px;">
					<li>Натисніть кнопку <strong>"Завантажити шаблон Excel"</strong> у меню "Дії"</li>
					<li>Відкрийте завантажений файл у Excel</li>
					<li>Заповніть всі необхідні поля в колонці <strong>"Значення для заповнення"</strong></li>
					<li>Збережіть файл</li>
					<li>Поверніться до цієї форми та прикріпіть файл у полі <strong>"Заповнена форма"</strong> нижче</li>
					<li>Після прикріплення натисніть <strong>"Імпортувати дані"</strong> у меню "Дії"</li>
				</ol>
				<div class="alert alert-warning" style="margin-top: 10px;">
					<strong>⚠ Важливо:</strong> Не змінюйте структуру файлу, назви колонок та ID показників!
				</div>
			</div>
		`;
		frm.fields_dict.download_template_html.$wrapper.html(html);
	}
}

function highlight_overdue(frm) {
	// Підсвітити прострочені звіти
	if (
		frm.doc.submission_deadline &&
		new Date(frm.doc.submission_deadline) < new Date() &&
		!["Імпортовано", "Прийнято"].includes(frm.doc.status)
	) {
		frm.dashboard.add_indicator(__("Прострочено!"), "red");

		const days_overdue = Math.floor(
			(new Date() - new Date(frm.doc.submission_deadline)) / (1000 * 60 * 60 * 24)
		);

		frappe.show_alert({
			message: __(`Звіт прострочений на ${days_overdue} днів!`),
			indicator: "red",
		});
	} else if (frm.doc.status === "Імпортовано" || frm.doc.status === "Прийнято") {
		frm.dashboard.add_indicator(__("Завершено"), "green");
	}
}

function auto_set_submission_deadline(frm) {
	// Автоматично встановити термін подання на основі періоду
	if (!frm.doc.submission_deadline && frm.doc.period && frm.doc.report_type) {
		let deadline_date;

		if (frm.doc.report_type === "Квартальний") {
			// Формат: YYYY-Q1
			const match = frm.doc.period.match(/^(\d{4})-Q(\d)$/);
			if (match) {
				const year = parseInt(match[1]);
				const quarter = parseInt(match[2]);

				// Дедлайн: 15 число місяця після закінчення кварталу
				const month = quarter * 3; // Останній місяць кварталу
				deadline_date = new Date(year, month, 15); // 15 число наступного місяця
			}
		} else if (frm.doc.report_type === "Річний") {
			// Формат: YYYY
			const year = parseInt(frm.doc.period);
			if (!isNaN(year)) {
				// Дедлайн: 31 січня наступного року
				deadline_date = new Date(year + 1, 0, 31);
			}
		}

		if (deadline_date) {
			frm.set_value("submission_deadline", deadline_date.toISOString().split("T")[0]);
		}
	}
}
