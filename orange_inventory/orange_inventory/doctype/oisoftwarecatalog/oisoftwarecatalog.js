frappe.ui.form.on("oiSoftwareCatalog", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.installations_count > 0) {
			frm.add_custom_button(
				__("{0} встановлень", [frm.doc.installations_count]),
				function () {
					frappe.set_route("List", "oiAgentSoftware", {
						catalog_entry: frm.doc.name,
					});
				},
				__("Перегляд")
			);
		}
	},
});
