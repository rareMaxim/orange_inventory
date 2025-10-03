// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiLocation", {
	refresh(frm) {
		frm.add_custom_button(__("Згенерувати лейбли"), () => {
			frappe
				.call({
					method: "orange_inventory.orange_inventory.doctype.oilocation.oilocationlabels.create_label_batch_from_location",
					args: { location: frm.doc.name },
				})
				.then((r) => {
					if (r.message && r.message.name) {
						frappe.set_route("Form", "oiAssetLabelBatch", r.message.name);
					}
				});
		});
	},
});
