// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiBasisDoc", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Переглянути активи"),
				function () {
					frappe.set_route("solution-assets", { decision: frm.doc.name });
				},
				__("Дії")
			);
		}
	},
});
