// Copyright (c) 2026, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiAgentCommand", {
	refresh: function (frm) {
		// Показуємо кнопку скасування для Pending команд
		if (frm.doc.status === "Pending" && !frm.is_new()) {
			frm.add_custom_button(
				__("Скасувати"),
				function () {
					frm.set_value("status", "Cancelled");
					frm.save();
				},
				__("Дії")
			);
		}

		// Показуємо кнопку повторного запуску для Failed/Timeout команд
		if (["Failed", "Timeout", "Cancelled"].includes(frm.doc.status) && !frm.is_new()) {
			frm.add_custom_button(
				__("Повторити"),
				function () {
					frappe.call({
						method: "frappe.client.insert",
						args: {
							doc: {
								doctype: "oiAgentCommand",
								agent: frm.doc.agent,
								command_type: frm.doc.command_type,
								command: frm.doc.command,
								arguments: frm.doc.arguments,
								timeout_seconds: frm.doc.timeout_seconds,
								status: "Pending",
							},
						},
						callback: function (r) {
							if (r.message) {
								frappe.show_alert({
									message: __("Команду додано в чергу"),
									indicator: "green",
								});
								frappe.set_route("Form", "oiAgentCommand", r.message.name);
							}
						},
					});
				},
				__("Дії")
			);
		}

		// Оновлюємо статус автоматично
		if (["Pending", "Sent", "Running"].includes(frm.doc.status) && !frm.is_new()) {
			setTimeout(function () {
				frm.reload_doc();
			}, 10000); // Оновлюємо кожні 10 секунд
		}
	},

	command_type: function (frm) {
		// Встановлюємо шаблони для різних типів команд
		if (frm.doc.command_type === "Restart Service") {
			frm.set_value("command", "Spooler");
			frm.set_df_property(
				"command",
				"description",
				"Введіть ім'я служби Windows (напр: Spooler, wuauserv)"
			);
		} else if (frm.doc.command_type === "Reboot") {
			frm.set_value("command", "Remote reboot initiated");
			frm.set_df_property("command", "read_only", 1);
		} else if (frm.doc.command_type === "Shutdown") {
			frm.set_value("command", "Remote shutdown initiated");
			frm.set_df_property("command", "read_only", 1);
		} else {
			frm.set_df_property("command", "read_only", 0);
			frm.set_df_property("command", "description", "Команда для виконання");
		}
	},
});

// Додаємо кнопку відправки команди на формі oiAgent
frappe.ui.form.on("oiAgent", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Виконати команду"),
				function () {
					// Діалог для вибору команди
					let d = new frappe.ui.Dialog({
						title: __("Виконати команду на агенті"),
						fields: [
							{
								label: __("Тип команди"),
								fieldname: "command_type",
								fieldtype: "Select",
								options: "PowerShell\nCMD\nRestart Service\nReboot\nShutdown",
								reqd: 1,
								default: "PowerShell",
							},
							{
								label: __("Команда"),
								fieldname: "command",
								fieldtype: "Code",
								options: "PowerShell",
								reqd: 1,
							},
							{
								label: __("Таймаут (сек)"),
								fieldname: "timeout_seconds",
								fieldtype: "Int",
								default: 60,
							},
						],
						primary_action_label: __("Виконати"),
						primary_action: function (values) {
							frappe.call({
								method: "frappe.client.insert",
								args: {
									doc: {
										doctype: "oiAgentCommand",
										agent: frm.doc.name,
										command_type: values.command_type,
										command: values.command,
										timeout_seconds: values.timeout_seconds,
										status: "Pending",
									},
								},
								callback: function (r) {
									if (r.message) {
										frappe.show_alert({
											message: __("Команду додано в чергу"),
											indicator: "green",
										});
										d.hide();
										frappe.set_route("Form", "oiAgentCommand", r.message.name);
									}
								},
							});
						},
					});
					d.show();
				},
				__("Дії")
			);
		}
	},
});
