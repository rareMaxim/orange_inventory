// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiCourseSubmission", {
	refresh(frm) {
		// Кнопка для автоматичного пошуку співробітника (тільки для адміністраторів)
		if (
			!frm.doc.__islocal &&
			!frm.doc.employee &&
			frappe.user.has_role(["System Manager", "Maintenance Manager"])
		) {
			frm.add_custom_button(__("Знайти співробітника"), function () {
				find_employee(frm);
			});
		}

		// Показуємо кнопку для швидкого відхилення
		if (
			!frm.doc.__islocal &&
			frm.doc.status === "Очікує обробки" &&
			frappe.user.has_role(["System Manager", "Maintenance Manager"])
		) {
			frm.add_custom_button(
				__("Відхилити"),
				function () {
					frm.set_value("status", "Відхилено");
					frm.save();
				},
				__("Дії")
			);

			frm.add_custom_button(
				__("Позначити як дублікат"),
				function () {
					frm.set_value("status", "Дублікат");
					frm.save();
				},
				__("Дії")
			);
		}
	},

	employee(frm) {
		// Коли вибрано співробітника, автоматично встановлюємо статус "Оброблено"
		if (frm.doc.employee && frm.doc.status === "Очікує обробки") {
			frm.set_value("status", "Оброблено");
		}
	},
});

function find_employee(frm) {
	frappe.call({
		method: "orange_inventory.orange_inventory.doctype.oicoursesubmission.oicoursesubmission.find_employee_by_name",
		args: {
			last_name: frm.doc.last_name,
			first_name: frm.doc.first_name,
			patronymic: frm.doc.patronymic,
		},
		callback: function (r) {
			if (r.message && r.message.length > 0) {
				// Якщо знайдено одного співробітника - автоматично встановлюємо
				if (r.message.length === 1) {
					frm.set_value("employee", r.message[0].name);
					frappe.show_alert({
						message: __("Знайдено співробітника: {0}", [r.message[0].full_name]),
						indicator: "green",
					});
				} else {
					// Якщо знайдено кілька - показуємо діалог вибору
					let options = r.message.map((emp) => ({
						label: `${emp.full_name} (${emp.organization || "без організації"})`,
						value: emp.name,
					}));

					frappe.prompt(
						{
							label: __("Виберіть співробітника"),
							fieldname: "employee",
							fieldtype: "Select",
							options: options.map((o) => o.value),
							reqd: 1,
						},
						function (values) {
							frm.set_value("employee", values.employee);
						},
						__("Знайдено кілька співробітників")
					);
				}
			} else {
				frappe.msgprint({
					title: __("Не знайдено"),
					message: __("Співробітника з таким ПІБ не знайдено в системі"),
					indicator: "orange",
				});
			}
		},
	});
}
