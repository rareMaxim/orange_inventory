// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiEmployee", {
	refresh(frm) {
		// Set query filter for organization field - only enabled organizations with ЄДРПОУ
		frm.set_query("organization", function () {
			return {
				filters: [
					["oiOrganization", "enabled", "=", 1],
					["oiOrganization", "tax_code", "!=", ""],
					["oiOrganization", "tax_code", "is", "set"],
				],
			};
		});

		// Set query filter for department field based on selected organization
		frm.set_query("department", function () {
			if (!frm.doc.organization) {
				// If no organization selected, show all organizations
				return {};
			}

			return {
				query: "orange_inventory.orange_inventory.doctype.oiemployee.oiemployee.get_department_query",
				filters: {
					organization: frm.doc.organization,
				},
			};
		});

		// Add button to print asset labels for this employee
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Друк етикеток активів"),
				function () {
					frappe.call({
						method: "orange_inventory.orange_inventory.doctype.oiemployee.oiemployee.create_label_batch_for_employee",
						args: {
							employee: frm.doc.name,
						},
						callback: function (r) {
							if (r.message) {
								frappe.set_route("Form", "oiAssetLabelBatch", r.message);
							}
						},
					});
				},
				__("Дії")
			);
		}
	},

	organization(frm) {
		// Clear department field when organization changes
		if (frm.doc.department) {
			frm.set_value("department", "");
		}

		// Refresh the department field query
		frm.set_query("department", function () {
			if (!frm.doc.organization) {
				return {};
			}

			return {
				query: "orange_inventory.orange_inventory.doctype.oiemployee.oiemployee.get_department_query",
				filters: {
					organization: frm.doc.organization,
				},
			};
		});
	},
});
