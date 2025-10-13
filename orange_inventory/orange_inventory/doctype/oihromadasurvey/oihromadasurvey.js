// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

// frappe.ui.form.on("oiHromadaSurvey", {
// 	refresh(frm) {

// 	},
// });
// qms_cherga / orange_inventory шлях підкоригуй під свій app
frappe.ui.form.on("oiHromadaSurvey", {
	onload(frm) {
		// update_value_display(frm);
	},
	refresh(frm) {
		if (frm.doc.type == "Група") {
			frm.add_custom_button("Recompute Group Scores", async () => {
				await frappe.call({
					method: "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.recompute_group_scores",
					args: { root: frm.doc.name },
				});
				await frm.reload_doc();
				frappe.show_alert({ message: "Scores recomputed", indicator: "green" });
			});
		}
	},
	type(frm) {
		update_value_display(frm);
	},
	bool_data(frm) {
		update_value_display(frm);
	},
	int_data(frm) {
		update_value_display(frm);
	},
	validate(frm) {
		update_value_display(frm);
	},
});

function update_value_display(frm) {
	if (frm.doc.type == "Група") {
		// Для вузлів-груп не показуємо значення
		frm.set_value("value_display", "");
		frm.set_value("is_group", 1);
		return;
	}

	const t = frm.doc.type;
	if (t === "Якісні дані") {
		// Показувати як Так/Ні (або 1/0 — вибери)
		const v = cint(frm.doc.bool_data) ? "Так" : "Ні";
		frm.set_value("value_display", v);
	} else if (t === "Кількісні дані") {
		frm.set_value("value_display", frm.doc.int_data ?? "0");
	} else {
		frm.set_value("value_display", "");
	}
}
