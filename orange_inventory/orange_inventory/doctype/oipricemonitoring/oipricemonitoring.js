// Copyright (c) 2025, IT MLT and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiPriceMonitoring", {
	refresh: function (frm) {
		// Add "Create Contract" button
		if (frm.doc.status === "Завершено" || frm.doc.status === "Затверджено") {
			frm.add_custom_button(
				__("Створити договір"),
				function () {
					frappe.call({
						method: "create_contract_from_monitoring",
						doc: frm.doc,
						callback: function (r) {
							if (r.message) {
								frappe.msgprint({
									title: __("Договір створено"),
									indicator: "green",
									message: __(
										'Створено договір: <a href="/app/oicontract/{0}">{0}</a>',
										[r.message]
									),
								});
								frm.reload_doc();
							}
						},
					});
				},
				__("Дії")
			);
		}
	},
});
