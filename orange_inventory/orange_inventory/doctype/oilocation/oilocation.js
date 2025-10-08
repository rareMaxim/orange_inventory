// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiLocation", {
	setup(frm) {
		// Перший завантаж — підтягаємо список
		load_city_options(frm);
	},
	city(frm) {
		load_city_options(frm, true);
	},
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

async function set_labels_suggestions(frm) {
	frappe.db
		.get_list(frm.doc.doctype, {
			fields: ["label"],
		})
		.then((records) => {
			if (records.length > 0) {
				const options = records.map((label) => ({
					value: label.label,
					label: label.label,
				}));
				frm.fields_dict.label.set_data(options);
			} else {
				frm.set_df_property("label", "options", []);
			}
		});
}

function load_city_options(frm, soft = false) {
	if (!frm.fields_dict.city) return;

	// Якщо вже є опції і soft=true — не дергай сервер зайвий раз
	const df = frm.fields_dict.city.df;
	if (soft && Array.isArray(df.options) && df.options.length) return;

	frappe
		.call({
			method: "orange_inventory.orange_inventory.doctype.oilocation.oilocation.get_city_options",
			args: { limit: 500 },
		})
		.then((r) => {
			const opts = r.message || [];
			frm.set_df_property("city", "options", opts); // для Autocomplete — масив рядків
		});
}
