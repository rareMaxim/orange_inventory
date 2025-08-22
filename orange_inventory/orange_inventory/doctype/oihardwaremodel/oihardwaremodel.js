// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiHardwareModel", {
	refresh(frm) {
		sync_ports_to_assets(frm);
	},
});

let sync_ports_to_assets = function (frm) {
	if (!frm.is_new() && frm.doc.is_network_device) {
		frm.add_custom_button(__("Синхронізувати порти з активами"), function () {
			frappe.call({
				method: "orange_inventory.orange_inventory.doctype.oihardwaremodel.oihardwaremodel.sync_ports_to_assets",
				args: {
					model_name: frm.doc.name,
				},
				// Повідомлення буде показано з серверної частини
			});
		}).addClass("btn-primary");
	}
};
