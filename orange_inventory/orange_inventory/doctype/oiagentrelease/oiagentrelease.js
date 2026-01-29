// Copyright (c) 2026, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiAgentRelease", {
	refresh(frm) {
		// Кнопка для завантаження файлу
		if (frm.doc.agent_file) {
			frm.add_custom_button(__("Завантажити агент"), function () {
				window.open(frm.doc.agent_file);
			});
		}
	},
});
