frappe.ui.form.on("oiAgentSoftware", {
	refresh(frm) {
		if (frm.doc.compliance_status === "Не в каталозі" && !frm.doc.catalog_entry) {
			frm.add_custom_button(
				__("Додати до каталогу"),
				function () {
					frappe.new_doc("oiSoftwareCatalog", {
						software_name: frm.doc.software_name,
						publisher: frm.doc.publisher || "",
					});
				},
				__("Дії")
			);
		}
	},
});
