// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

// frappe.ui.form.on("oiDecommissioningAct", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on("oiDecommissioningAct", {
	refresh(frm) {
		if (frm.doc.docstatus !== 2 && !frm.doc.correspondence) {
			frm.add_custom_button(__("Створити службовий лист на списання"), async () => {
				if (frm.is_dirty()) await frm.save();
				frappe.call({
					// новий dotted path у контролері DocType
					method: "orange_inventory.orange_inventory.doctype.oidecommissioningact.oidecommissioningact.create_correspondence_for_act",
					args: { act_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Готуємо службовий лист..."),
					callback: (r) => {
						if (r?.message) {
							frm.set_value("correspondence", r.message);
							frm.save().then(() =>
								frappe.set_route("Form", "oiCorrespondence", r.message)
							);
						}
					},
				});
			});
		}

		if (frm.doc.correspondence) {
			frm.add_custom_button(__("Відкрити службовий лист"), () => {
				frappe.set_route("Form", "oiCorrespondence", frm.doc.correspondence);
			});
		}
	},
});
