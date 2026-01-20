// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiServiceRequest", {
	refresh(frm) {
		// Додаємо кастомні кнопки залежно від статусу
		add_custom_buttons(frm);

		// Фільтри для полів
		setup_field_filters(frm);

		// Встановлюємо значення за замовчуванням для нових заявок
		if (frm.is_new()) {
			set_default_values(frm);
		}

		// Показуємо статистику часу
		show_time_statistics(frm);
	},

	status(frm) {
		// Автоматично встановлюємо дату завершення
		if (frm.doc.status === "Виконана" && !frm.doc.completion_date) {
			frm.set_value("completion_date", frappe.datetime.now_date());
		}
	},

	priority(frm) {
		// Автоматично встановлюємо планову дату залежно від пріоритету
		if (frm.is_new() && frm.doc.priority && !frm.doc.due_date) {
			let days_to_add = get_days_by_priority(frm.doc.priority);
			let due_date = frappe.datetime.add_days(frappe.datetime.now_date(), days_to_add);
			frm.set_value("due_date", due_date);
		}
	},
});

function add_custom_buttons(frm) {
	// Очищуємо попередні кнопки
	frm.custom_buttons = {};

	if (!frm.is_new()) {
		// Кнопка "Призначити мені"
		if (!frm.doc.assigned_to && frm.doc.status === "Нова") {
			frm.add_custom_button(__("Призначити мені"), function () {
				assign_to_current_user(frm);
			}).addClass("btn-primary");
		}

		// Кнопка "Розпочати роботу"
		if (frm.doc.status === "Прийнята" || frm.doc.status === "Нова") {
			frm.add_custom_button(__("Розпочати роботу"), function () {
				start_work(frm);
			}).addClass("btn-success");
		}

		// Кнопка "Завершити роботу"
		if (frm.doc.status === "В роботі" || frm.doc.status === "Очікує підтвердження") {
			frm.add_custom_button(__("Завершити роботу"), function () {
				complete_work_dialog(frm);
			}).addClass("btn-success");
		}

		// Кнопка "Додати коментар"
		frm.add_custom_button(__("Додати коментар"), function () {
			add_comment_dialog(frm);
		});

		// Кнопка "Створити пов'язану заявку"
		frm.add_custom_button(__("Створити пов'язану заявку"), function () {
			create_related_request(frm);
		});

		// Кнопка "Друк"
		frm.add_custom_button(__("Друк"), function () {
			frappe.utils.print(frm.doctype, frm.docname, "Service Request Print Format");
		});
	}
}

function setup_field_filters(frm) {
	// Фільтр для заявника - тільки співробітники поточної організації
	frm.set_query("requester", function () {
		return {
			filters: {
				status: ["in", "Працює очно, Працює віддалено"],
			},
		};
	});

	// Фільтр для виконавця - тільки IT співробітники
	frm.set_query("assigned_to", function () {
		return {
			filters: {
				status: ["in", "Працює очно, Працює віддалено"],
			},
		};
	});

	// Фільтр для активу - тільки активи організації заявника
	frm.set_query("related_asset", function () {
		if (frm.doc.requester_organization) {
			return {
				filters: {
					// current_owner: frm.doc.requester_organization,
					status: ["!=", "Списано"],
				},
			};
		}
		return {};
	});
}

function set_default_values(frm) {
	// Встановлюємо поточного користувача як заявника, якщо це можливо
	frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: "hromsEmployee",
			filters: { user_id: frappe.session.user },
			fieldname: "name",
		},
		callback: function (r) {
			if (r.message && r.message.name) {
				frm.set_value("requester", r.message.name);
			}
		},
	});
}

function show_time_statistics(frm) {
	if (!frm.doc.creation) return; // У нових документах дати створення ще немає

	// Використовуємо утиліти frappe.datetime для різниці в днях
	let days_open = frappe.datetime.get_diff(
		frappe.datetime.now_date(),
		frm.doc.creation.substring(0, 10)
	);

	// Створюємо HTML-блок, додаючи унікальний клас `time-statistics-block`
	let time_info = `<div class="alert alert-info time-statistics-block">
        <strong>Час з моменту створення:</strong> ${days_open} днів<br>`;

	if (frm.doc.due_date) {
		let days_until_due = frappe.datetime.get_diff(
			frm.doc.due_date,
			frappe.datetime.now_date()
		);

		if (days_until_due < 0) {
			time_info += `<strong style="color: red;">Прострочено на:</strong> ${Math.abs(
				days_until_due
			)} днів<br>`;
		} else {
			time_info += `<strong>Залишилось днів:</strong> ${days_until_due} днів<br>`;
		}
	}

	// 2. ВИРІШЕННЯ ПРОБЛЕМИ З DURATION
	if (frm.doc.estimated_hours > 0 && frm.doc.actual_hours > 0) {
		// Різниця буде в секундах
		let diff_in_seconds = frm.doc.actual_hours - frm.doc.estimated_hours;

		// Визначаємо знак відхилення
		let deviation_prefix = diff_in_seconds >= 0 ? "+" : "-";

		// Конвертуємо секунди (по модулю) в рядок "1г 30хв 15с"
		let formatted_diff = format_duration_custom(diff_in_seconds);

		time_info += `<strong>Відхилення від плану:</strong> ${deviation_prefix}${formatted_diff}`;
	}

	time_info += "</div>";

	// Додаємо оновлену інформацію після поля статус
	const html_content = $(time_info);
	frm.fields_dict.time_statistics_html.html(html_content);
}

function get_days_by_priority(priority) {
	const priority_days = {
		Критичний: 1,
		Високий: 3,
		Середній: 7,
		Низький: 14,
	};
	return priority_days[priority] || 7;
}

function assign_to_current_user(frm) {
	frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: "hromsEmployee",
			filters: { user_id: frappe.session.user },
			fieldname: "name",
		},
		callback: function (r) {
			if (r.message && r.message.name) {
				frappe.call({
					doc: frm.doc,
					method: "assign_to_user",
					args: {
						user: r.message.name,
					},
					callback: function (response) {
						frm.reload_doc();
						frappe.show_alert({
							message: __("Заявка призначена вам"),
							indicator: "green",
						});
					},
				});
			}
		},
	});
}

function start_work(frm) {
	frappe.confirm(__("Розпочати роботу над цією заявкою?"), function () {
		frappe.call({
			doc: frm.doc,
			method: "start_work",
			callback: function (r) {
				frm.reload_doc();
				frappe.show_alert({
					message: __("Роботу розпочато"),
					indicator: "green",
				});
			},
		});
	});
}

function complete_work_dialog(frm) {
	let d = new frappe.ui.Dialog({
		title: __("Завершення роботи"),
		fields: [
			{
				label: "Опис виконаних робіт",
				fieldname: "resolution",
				fieldtype: "Long Text",
				reqd: 1,
				description: __("Опишіть що було зроблено для вирішення проблеми"),
			},
			{
				label: "Фактично витрачено годин",
				fieldname: "actual_hours",
				fieldtype: "Duration",
				default: frm.doc.actual_hours || 0,
			},
		],
		primary_action_label: __("Завершити"),
		primary_action(values) {
			frm.set_value("resolution", values.resolution);
			frm.set_value("actual_hours", values.actual_hours);

			frappe.call({
				doc: frm.doc,
				method: "complete_work",
				args: {
					resolution: values.resolution,
				},
				callback: function (r) {
					frm.reload_doc();
					frappe.show_alert({
						message: __("Роботу завершено"),
						indicator: "green",
					});
					d.hide();
				},
			});
		},
	});
	d.show();
}

function add_comment_dialog(frm) {
	let d = new frappe.ui.Dialog({
		title: __("Додати коментар"),
		fields: [
			{
				label: "Коментар",
				fieldname: "comment",
				fieldtype: "Long Text",
				reqd: 1,
			},
		],
		primary_action_label: __("Додати"),
		primary_action(values) {
			frappe.call({
				doc: frm.doc,
				method: "add_comment",
				args: {
					comment: values.comment,
				},
				callback: function (r) {
					frm.reload_doc();
					frappe.show_alert({
						message: __("Коментар додано"),
						indicator: "green",
					});
					d.hide();
				},
			});
		},
	});
	d.show();
}

function create_related_request(frm) {
	frappe.route_options = {
		related_asset: frm.doc.related_asset,
		requester: frm.doc.requester,
	};
	frappe.new_doc("oiServiceRequest");
}

/**
 * Перетворює загальну кількість секунд у читабельний формат (дні, години, хвилини, секунди).
 * @param {number} total_seconds - Загальна кількість секунд.
 * @returns {string} - Відформатований рядок, наприклад "1год 30хв".
 */
function format_duration_custom(total_seconds) {
	if (total_seconds === 0) {
		return "0с";
	}

	const days = Math.floor(total_seconds / 86400);
	total_seconds %= 86400;
	const hours = Math.floor(total_seconds / 3600);
	total_seconds %= 3600;
	const minutes = Math.floor(total_seconds / 60);
	const seconds = total_seconds % 60;

	let parts = [];
	if (days > 0) {
		parts.push(days + "дн");
	}
	if (hours > 0) {
		parts.push(hours + "год");
	}
	if (minutes > 0) {
		parts.push(minutes + "хв");
	}
	if (seconds > 0) {
		parts.push(seconds + "с");
	}

	return parts.join(" ");
}
